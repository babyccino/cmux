//! `cmux setup` driven the way an agent drives it: read `list` and `status`,
//! run the fix `status` names, run it again, then run the `undo` the result
//! names, reading only the JSON each step prints. A fake HOME, acpmux home
//! and PATH (with fake harness CLIs), so nothing of the person's is read or
//! written.
#![cfg(unix)]

use std::io::{BufRead, BufReader, Write};
use std::os::unix::net::UnixListener;
use std::path::{Path, PathBuf};
use std::process::{Command, Output, Stdio};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use serde_json::{Value, json};

struct World {
    home: PathBuf,
    acpmux: PathBuf,
    repo: PathBuf,
    /// The fake harness CLIs, first on PATH.
    bin: PathBuf,
    /// Where `cmux setup` looks for an acpmux daemon.
    socket: PathBuf,
}

impl World {
    fn new(name: &str) -> Self {
        static NEXT: AtomicU64 = AtomicU64::new(0);
        let n = NEXT.fetch_add(1, Ordering::Relaxed);
        let stamp = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos() % 1_000_000;
        // Short: Unix socket paths are limited to about 100 bytes.
        let dir = Path::new("/tmp").join(format!("cxs-{name}-{}-{stamp}-{n}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        // The real folder (/tmp is /private/tmp on macOS): a harness's install
        // channel is read from where its file really is, under HOME.
        let dir = std::fs::canonicalize(dir).unwrap();
        let world = Self {
            home: dir.join("home"),
            acpmux: dir.join("acpmux"),
            repo: dir.join("work").join("repo"),
            bin: dir.join("bin"),
            socket: dir.join("d.sock"),
        };
        for path in [&world.home, &world.acpmux, &world.repo, &world.bin] {
            std::fs::create_dir_all(path).unwrap();
        }
        world
    }

    /// The folder as acpmux keys it.
    fn folder(&self) -> String {
        std::fs::canonicalize(&self.repo).unwrap().to_string_lossy().into_owned()
    }

    fn record(&self) -> Option<Value> {
        let text = std::fs::read_to_string(self.acpmux.join("trust.json")).ok()?;
        Some(serde_json::from_str(&text).unwrap())
    }

    fn run(&self, args: &[&str]) -> Output {
        Command::new(env!("CARGO_BIN_EXE_cmux-tui"))
            .args(args)
            .current_dir(&self.repo)
            .env("HOME", &self.home)
            .env("ACPMUX_HOME", &self.acpmux)
            .env("ACPMUX_SOCKET", &self.socket)
            .env("PATH", self.path())
            .env("LC_ALL", "C")
            .env_remove("XDG_CONFIG_HOME")
            .env_remove("XDG_DATA_HOME")
            .env_remove("CMUX_NEXT_CONFIG_FILE")
            .env_remove("ACPMUX_SESSION_ID")
            .env_remove("ACPMUX_AGENT_LAUNCH")
            .env_remove("CMUX_AGENTS_DISABLED")
            .env_remove("CLAUDE_CONFIG_DIR")
            .env_remove("CODEX_HOME")
            .env_remove("CMUX_SOCKET_PATH")
            .stdin(Stdio::null())
            .output()
            .unwrap()
    }

    /// Runs `args`, expects exit 0 and one JSON object on stdout.
    fn json(&self, args: &[&str]) -> Value {
        let output = self.run(args);
        assert!(
            output.status.success(),
            "{args:?} exited {:?}: {}",
            output.status.code(),
            String::from_utf8_lossy(&output.stderr)
        );
        serde_json::from_slice(&output.stdout).unwrap_or_else(|error| {
            panic!("{args:?}: {error}: {}", String::from_utf8_lossy(&output.stdout))
        })
    }

    /// The fake CLIs, OpenCode's own installer folder, and the system's tools
    /// the fakes use: no harness of the machine's own is found.
    fn path(&self) -> String {
        format!("{}:{}:/usr/bin:/bin", self.bin.display(), self.opencode_bin().display())
    }

    /// Where OpenCode's own installer puts it (`~/.opencode/bin`), which
    /// updates itself with `opencode upgrade`.
    fn opencode_bin(&self) -> PathBuf {
        self.home.join(".opencode").join("bin")
    }

    /// A fake ACP harness CLI at `path`: `--version` prints `version`; on
    /// stdin it answers `initialize`, and `session/new` with ACP's
    /// "authentication required" until `signed_in(path)` exists. Every line
    /// it reads goes to `path.log`. A short-lived `sh` writes it so no sibling
    /// test's fork inherits a write descriptor (ETXTBSY).
    fn harness(&self, path: &Path, version: &str) {
        std::fs::create_dir_all(path.parent().unwrap()).unwrap();
        let script = format!(
            r#"#!/bin/sh
[ "$1" = --version ] && {{ echo "{version}"; exit 0; }}
while IFS= read -r line; do
  printf '%s\n' "$line" >>"$0.log"
  id=${{line#*\"id\":}}; id=${{id%%,*}}
  case $line in
    *'"method":"initialize"'*)
      printf '{{"jsonrpc":"2.0","id":%s,"result":{{"protocolVersion":1,"authMethods":[{{"id":"oauth","name":"Sign in"}}]}}}}\n' "$id" ;;
    *'"method":"session/new"'*)
      if [ -e "$0.signed-in" ]; then
        printf '{{"jsonrpc":"2.0","id":%s,"result":{{"sessionId":"s1"}}}}\n' "$id"
      else
        printf '{{"jsonrpc":"2.0","id":%s,"error":{{"code":-32000,"message":"Authentication required"}}}}\n' "$id"
      fi ;;
  esac
done
"#
        );
        let mut child = Command::new("/bin/sh")
            .args(["-c", "cat >\"$1\" && chmod 755 \"$1\"", "sh"])
            .arg(path)
            .stdin(Stdio::piped())
            .spawn()
            .unwrap();
        child.stdin.take().unwrap().write_all(script.as_bytes()).unwrap();
        assert!(child.wait().unwrap().success());
    }

    /// What the fake harness at `path` read.
    fn harness_log(path: &Path) -> String {
        std::fs::read_to_string(format!("{}.log", path.display())).unwrap_or_default()
    }

    /// The person finishing the sign-in of the fake harness at `path`.
    fn sign_in(path: &Path) {
        std::fs::write(format!("{}.signed-in", path.display()), "").unwrap();
    }

    /// Every file under the acpmux home, with its bytes.
    fn acpmux_files(&self) -> Vec<(PathBuf, Vec<u8>)> {
        let mut files = Vec::new();
        let mut dirs = vec![self.acpmux.clone()];
        while let Some(dir) = dirs.pop() {
            for entry in std::fs::read_dir(&dir).unwrap() {
                let path = entry.unwrap().path();
                if path.is_dir() {
                    dirs.push(path);
                } else {
                    let bytes = std::fs::read(&path).unwrap();
                    files.push((path, bytes));
                }
            }
        }
        files.sort();
        files
    }

    /// Runs a command a result named (`cmux setup ...`), as an agent's shell would.
    fn follow(&self, command: &str) -> Value {
        let words = shell_words(command);
        assert_eq!(words.first().map(String::as_str), Some("cmux"), "{command}");
        self.json(&words[1..].iter().map(String::as_str).collect::<Vec<_>>())
    }
}

/// Splits a command the way sh does for the quoting `cmux setup` writes:
/// bare words and single-quoted words.
fn shell_words(command: &str) -> Vec<String> {
    let mut words = Vec::new();
    let mut word = String::new();
    let mut quoted = false;
    let mut chars = command.chars().peekable();
    while let Some(c) = chars.next() {
        match c {
            '\'' => quoted = !quoted,
            '\\' if !quoted => word.extend(chars.next()),
            ' ' if !quoted => {
                if !word.is_empty() {
                    words.push(std::mem::take(&mut word));
                }
            }
            c => word.push(c),
        }
    }
    if !word.is_empty() {
        words.push(word);
    }
    words
}

#[test]
fn cmux_setup_trust_an_agent_runs_the_fix_reruns_it_and_undoes_it() {
    let world = World::new("trust");
    let folder = world.folder();
    let claude_json = world.home.join(".claude.json");
    std::fs::write(&claude_json, r#"{"projects":{}}"#).unwrap();

    // The agent reads where things stand.
    let status = world.json(&["setup", "status"]);
    let check = &status["checks"][0];
    assert_eq!(check["task"], "trust", "{status}");
    assert_eq!(check["state"], "needs_setup", "{status}");
    assert_eq!(check["folder"], folder.as_str());
    let fix = check["fix"].as_str().expect("status names its fix").to_owned();

    // A dry run plans and writes nothing.
    let planned = world.json(&["setup", "trust", "--dry-run"]);
    assert_eq!(planned["state"], "planned", "{planned}");
    assert_eq!(planned["dry_run"], true);
    assert!(planned["undo"].is_string(), "{planned}");
    assert_eq!(world.record(), None, "a dry run wrote the record");

    // The fix status named.
    let changed = world.follow(&fix);
    assert_eq!(changed["state"], "changed", "{changed}");
    assert_eq!(changed["via"], "record");
    assert_eq!(changed["before"]["level"], "unknown");
    assert_eq!(changed["after"]["level"], "trusted");
    assert_eq!(world.record(), Some(json!({folder.as_str(): "trusted"})));
    let undo = changed["undo"].as_str().expect("a change names its undo").to_owned();

    // Again: nothing to do, nothing written.
    let again = world.json(&["setup", "trust", &folder]);
    assert_eq!(again["state"], "ok", "{again}");
    assert_eq!(again["undo"], Value::Null);
    assert_eq!(world.json(&["setup", "status"])["checks"][0]["state"], "ok");

    // The undo puts the record back the way it was.
    let undone = world.follow(&undo);
    assert_eq!(undone["state"], "changed", "{undone}");
    assert_eq!(undone["after"]["level"], "unknown");
    assert_eq!(world.record(), Some(json!({})));

    // A refusal is recorded the same way, and its undo clears it.
    let refused = world.json(&["setup", "trust", ".", "--level", "untrusted"]);
    assert_eq!(refused["after"]["level"], "untrusted", "{refused}");
    assert_eq!(refused["undo"], format!("cmux setup trust {folder} --level unknown"));

    // Claude Code's own file has one writer, and it is not cmux.
    assert_eq!(std::fs::read_to_string(&claude_json).unwrap(), r#"{"projects":{}}"#);
}

#[test]
fn cmux_setup_trust_goes_through_a_running_acpmux_daemon() {
    let world = World::new("daemon");
    let folder = world.folder();
    let requests = Arc::new(Mutex::new(Vec::new()));
    let listener = UnixListener::bind(&world.socket).unwrap();
    let seen = requests.clone();
    std::thread::spawn(move || {
        let (stream, _) = listener.accept().unwrap();
        stream.set_read_timeout(Some(Duration::from_secs(20))).unwrap();
        let mut reader = BufReader::new(stream.try_clone().unwrap());
        let mut writer = stream;
        let mut line = String::new();
        while reader.read_line(&mut line).unwrap_or(0) > 0 {
            let request: Value = serde_json::from_str(&line).unwrap();
            line.clear();
            let result = match request["method"].as_str() {
                Some("initialize") => json!({"protocolVersion": 1}),
                _ => json!({"cwd": request["params"]["cwd"], "level": request["params"]["level"]}),
            };
            seen.lock().unwrap().push(request.clone());
            let reply = json!({"jsonrpc": "2.0", "id": request["id"], "result": result});
            if writeln!(writer, "{reply}").is_err() {
                break;
            }
        }
    });

    let changed = world.json(&["setup", "trust"]);
    assert_eq!(changed["state"], "changed", "{changed}");
    assert_eq!(changed["via"], "daemon");
    let requests = requests.lock().unwrap();
    let set = requests
        .iter()
        .find(|request| request["method"] == "acp.trust.set")
        .unwrap_or_else(|| panic!("no acp.trust.set in {requests:?}"));
    assert_eq!(set["params"], json!({"cwd": folder, "level": "trusted"}));
    assert_eq!(world.record(), None, "the CLI wrote the record beside the daemon");
}

#[test]
fn cmux_setup_list_names_every_task_and_bad_arguments_exit_2() {
    let world = World::new("list");
    let list = world.json(&["setup", "list"]);
    let tasks = list["tasks"].as_array().unwrap();
    let ids = tasks.iter().map(|task| task["id"].as_str().unwrap()).collect::<Vec<_>>();
    for id in ["trust", "harness", "machine", "accounts", "computer_use", "team_invites"] {
        assert!(ids.contains(&id), "{id} missing from {ids:?}");
    }
    for task in tasks {
        assert!(task["summary"].is_string(), "{task}");
        assert!(task["apply"].as_array().is_some_and(|apply| !apply.is_empty()), "{task}");
    }
    assert_eq!(world.json(&["setup"]), list);

    for args in [
        &["setup", "nope"][..],
        &["setup", "trust", "--level", "maybe"],
        &["setup", "trust", "a", "b"],
        &["setup", "list", "extra"],
    ] {
        let output = world.run(args);
        assert_eq!(output.status.code(), Some(2), "{args:?}");
        let error: Value = serde_json::from_slice(&output.stderr).unwrap();
        assert_eq!(error["code"], "usage.invalid", "{args:?}");
    }
    assert_eq!(world.record(), None);
}

#[test]
fn cmux_setup_harness_an_agent_hands_the_person_the_sign_in_and_checks_again() {
    let world = World::new("harness");
    let gemini = world.bin.join("gemini");
    world.harness(&gemini, "gemini 0.1.0");
    let opencode = world.opencode_bin().join("opencode");
    world.harness(&opencode, "1.0.0");
    World::sign_in(&opencode);
    // The daemon's last check read a newer OpenCode than this one.
    let saved = json!([{
        "id": "opencode", "program": opencode, "path": opencode, "channel": "native",
        "package": "opencode-ai", "version": "1.0.0", "latest": "9.9.9",
        "latestCheckedAt": 1, "outdated": true, "auth": "signedIn", "checkedAt": 1,
    }]);
    std::fs::write(world.acpmux.join("harness-health.json"), saved.to_string()).unwrap();
    let before = world.acpmux_files();

    // `setup list` names the command, and `setup status` finds the sign-in.
    let list = world.json(&["setup", "list"]);
    let task = list["tasks"].as_array().unwrap().iter().find(|t| t["id"] == "harness").unwrap();
    assert_eq!(task["setup"], "cmux setup harness [ID ...] [--dry-run]", "{task}");
    let status = world.json(&["setup", "status"]);
    let check = &status["checks"][1];
    assert_eq!(check["task"], "harness", "{status}");
    assert_eq!(check["state"], "needs_user", "{status}");
    assert_eq!(check["user_action"]["command"], "cmux harness login gemini", "{status}");

    // Every configured or found harness; UniiChat, offered everywhere, is not one.
    let all = world.json(&["setup", "harness"]);
    assert_eq!(all["task"], "harness", "{all}");
    assert_eq!(all["state"], "needs_user", "{all}");
    assert_eq!(all["dry_run"], false);
    assert_eq!(all["undo"], Value::Null);
    let ids = all["harnesses"].as_array().unwrap().iter().map(|h| &h["id"]).collect::<Vec<_>>();
    assert_eq!(ids, [&json!("gemini"), &json!("opencode")], "{all}");
    let signed_out = &all["harnesses"][0];
    assert_eq!(signed_out["state"], "needs_user", "{signed_out}");
    assert_eq!(signed_out["installed"], true);
    assert_eq!(signed_out["configured"], true);
    assert_eq!(signed_out["version"], "0.1.0");
    assert_eq!(signed_out["signed_in"], false, "{signed_out}");
    let action = &signed_out["user_action"];
    assert_eq!(action["kind"], "oauth", "{action}");
    assert_eq!(action["command"], "cmux harness login gemini");
    assert!(action["text"].as_str().is_some_and(|text| !text.is_empty()), "{action}");
    assert_eq!(all["user_action"], *action, "the task names the first thing to do");
    let current = &all["harnesses"][1];
    assert_eq!(current["state"], "ok", "{current}");
    assert_eq!(current["signed_in"], true, "{current}");
    assert_eq!(current["outdated"], true, "{current}");
    assert_eq!(current["latest"], "9.9.9");
    let update = current["update"].as_str().expect("an outdated harness names its update");
    assert!(update.ends_with(" upgrade"), "{update}");
    assert_eq!(current["user_action"], Value::Null);

    // A harness that is not installed: its shipped profile's docs.
    let missing = world.json(&["setup", "harness", "codex"]);
    assert_eq!(missing["state"], "needs_user", "{missing}");
    let codex = &missing["harnesses"][0];
    assert_eq!(codex["id"], "codex", "{missing}");
    assert_eq!(codex["configured"], false, "{codex}");
    assert_eq!(codex["installed"], false, "{codex}");
    assert_eq!(codex["user_action"]["kind"], "install", "{codex}");
    assert_eq!(codex["user_action"]["url"], "https://developers.openai.com/codex/cli");

    // The person signs in; the agent checks that harness again.
    World::sign_in(&gemini);
    let again = world.json(&["setup", "harness", "gemini", "--dry-run"]);
    assert_eq!(again["state"], "ok", "{again}");
    assert_eq!(again["dry_run"], true);
    assert_eq!(again["user_action"], Value::Null);
    assert_eq!(again["harnesses"][0]["signed_in"], true, "{again}");
    assert_eq!(world.json(&["setup", "status"])["checks"][1]["state"], "ok");

    // A status check: no prompt turn (that is `cmux harness doctor`), nothing written.
    for log in [World::harness_log(&gemini), World::harness_log(&opencode)] {
        assert!(log.contains("\"session/new\""), "{log}");
        assert!(!log.contains("session/prompt"), "{log}");
    }
    assert_eq!(world.acpmux_files(), before, "setup harness wrote acpmux state");

    for args in [&["setup", "harness", "nope"][..], &["setup", "harness", "--bogus"]] {
        let output = world.run(args);
        assert_eq!(output.status.code(), Some(2), "{args:?}");
        let error: Value = serde_json::from_slice(&output.stderr).unwrap();
        assert_eq!(error["code"], "usage.invalid", "{args:?}");
    }
}

#[test]
fn cmux_setup_harness_with_none_installed_asks_for_one() {
    let world = World::new("noharness");
    let none = world.json(&["setup", "harness"]);
    assert_eq!(none["state"], "needs_user", "{none}");
    assert_eq!(none["harnesses"], json!([]));
    assert_eq!(none["user_action"]["kind"], "install", "{none}");
    assert!(none["user_action"]["url"].is_string(), "{none}");
}
