#!/usr/bin/env bash
# 创建 GitHub 公开仓库并推送（Token 用完即从本地配置中抹除，不落盘）
#
# 用法：
#   export GH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
#   bash scripts/push_to_github.sh [用户名] [仓库名]
#
set -euo pipefail

USER="${1:-wojiushilyj}"
REPO="${2:-AI_urban_plan}"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"

if [[ -z "${GH_TOKEN:-}" ]]; then
  echo "错误：请先设置环境变量 GH_TOKEN（GitHub Personal Access Token，需 repo 权限）"
  echo "  export GH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx"
  exit 1
fi

echo "==> 1/4 创建远端公开仓库 ${USER}/${REPO}"
RESP=".gh_resp.json"
# 注意：curl 失败时用 || echo 兜底，避免 set -e 让脚本在拿到状态码前就中断
HTTP=$(curl -s -o "$RESP" -w "%{http_code}" \
  -H "Authorization: Bearer ${GH_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  -d "{\"name\":\"${REPO}\",\"private\":false,\"description\":\"国土 AI 竞赛｜多场景智慧选址系统（2026 AI+国土空间治理创新应用大赛 · 数智场景赛道）\"}" \
  "https://api.github.com/user/repos" || echo "000")

if [[ "$HTTP" == "201" ]]; then
  echo "    创建成功"
elif [[ "$HTTP" == "422" ]]; then
  echo "    仓库已存在，直接推送"
else
  echo "    失败（HTTP $HTTP）"
  [[ -f "$RESP" ]] && cat "$RESP"
  rm -f "$RESP"
  exit 1
fi
rm -f "$RESP"

echo "==> 2/4 绑定远端（临时带 Token）"
git remote remove origin 2>/dev/null || true
git remote add origin "https://${USER}:${GH_TOKEN}@github.com/${USER}/${REPO}.git"

echo "==> 3/4 推送 ${BRANCH}"
git push -u origin "${BRANCH}"

echo "==> 4/4 从本地配置中移除 Token"
git remote set-url origin "https://github.com/${USER}/${REPO}.git"
unset GH_TOKEN

echo ""
echo "完成：https://github.com/${USER}/${REPO}"
