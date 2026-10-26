set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
date -u
findmnt -T "$B"
df -h "$B"
nvidia-smi --query-gpu=index,name,uuid,memory.used --format=csv,noheader
nvidia-smi --query-compute-apps=pid,gpu_uuid,used_memory --format=csv,noheader
find "$B/models" -maxdepth 2 -name config.json -print
git ls-remote https://github.com/zhouz4884-coder/RevTrace.git refs/heads/main
