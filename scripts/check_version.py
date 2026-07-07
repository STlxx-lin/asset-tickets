import os
import re
import subprocess
import sys

def get_version_from_content(content):
    m = re.search(r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", content)
    return m.group(1) if m else None

def get_current_version():
    try:
        with open("src/core/config.py", "r", encoding="utf-8") as f:
            return get_version_from_content(f.read())
    except Exception as e:
        print(f"Error reading current config: {e}")
        return None

def get_git_file_content(ref, filepath):
    try:
        res = subprocess.run(
            ["git", "show", f"{ref}:{filepath}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True
        )
        return res.stdout
    except Exception as e:
        print(f"Error getting file content for {ref}:{filepath}: {e}")
        return None

def main():
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    ref = os.environ.get("GITHUB_REF", "")
    
    print(f"Event: {event_name}, Ref: {ref}")
    
    current_version = get_current_version()
    if not current_version:
        print("Could not find APP_VERSION in current src/core/config.py")
        sys.exit(1)
    print(f"Current APP_VERSION: {current_version}")
    
    version_changed = False
    
    if event_name == "workflow_dispatch":
        print("Manual trigger (workflow_dispatch). Forcing build.")
        version_changed = True
        
    elif ref.startswith("refs/tags/"):
        tag_name = ref.replace("refs/tags/", "")
        print(f"Tag push detected: {tag_name}. Forcing build.")
        version_changed = True
        
    elif event_name == "pull_request":
        base_ref = os.environ.get("GITHUB_BASE_REF", "")
        if base_ref:
            print(f"PR base ref: {base_ref}")
            base_content = get_git_file_content(f"origin/{base_ref}", "src/core/config.py")
            if not base_content:
                base_content = get_git_file_content(base_ref, "src/core/config.py")
                
            if base_content:
                base_version = get_version_from_content(base_content)
                print(f"Base version: {base_version}")
                if base_version != current_version:
                    version_changed = True
                    print(f"Version changed from {base_version} to {current_version}")
                else:
                    print("Version unchanged in PR.")
            else:
                print("Could not retrieve base version. Defaulting to changed.")
                version_changed = True
        else:
            version_changed = True
            
    elif event_name == "push":
        before_sha = os.environ.get("GITHUB_EVENT_BEFORE", "")
        print(f"Before SHA: {before_sha}")
        
        if before_sha and before_sha != "0000000000000000000000000000000000000000":
            before_content = get_git_file_content(before_sha, "src/core/config.py")
            if before_content:
                before_version = get_version_from_content(before_content)
                print(f"Before version: {before_version}")
                if before_version != current_version:
                    version_changed = True
                    print(f"Version changed from {before_version} to {current_version}")
                else:
                    print("Version unchanged in push.")
            else:
                print("Could not retrieve before version. Defaulting to changed.")
                version_changed = True
        else:
            before_content = get_git_file_content("HEAD~1", "src/core/config.py")
            if before_content:
                before_version = get_version_from_content(before_content)
                print(f"Before version (HEAD~1): {before_version}")
                if before_version != current_version:
                    version_changed = True
                    print(f"Version changed from {before_version} to {current_version}")
                else:
                    print("Version unchanged compared to HEAD~1.")
            else:
                print("No historical commit found. Treating as version changed.")
                version_changed = True
    else:
        # 其他事件，例如本地直接运行脚本测试时
        print(f"Other event '{event_name}' or local test run. Checking against HEAD~1...")
        before_content = get_git_file_content("HEAD~1", "src/core/config.py")
        if before_content:
            before_version = get_version_from_content(before_content)
            print(f"Before version (HEAD~1): {before_version}")
            if before_version != current_version:
                version_changed = True
                print(f"Version changed from {before_version} to {current_version}")
            else:
                print("Version unchanged compared to HEAD~1.")
        else:
            print("No historical commit found. Defaulting to changed.")
            version_changed = True

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"version_changed={'true' if version_changed else 'false'}\n")
            f.write(f"version_tag={current_version}\n")
        print(f"Wrote outputs: version_changed={'true' if version_changed else 'false'}, version_tag={current_version}")
    else:
        print("GITHUB_OUTPUT environment variable not set. (Local test)")

if __name__ == "__main__":
    main()
