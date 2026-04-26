# Skill 更新工作流

**重要前提**：Multica Agent 运行时只读取数据库中的 skill，不读取本地文件系统中的 `.claude/skills/` 目录。因此每次修改 skill 后，必须执行完整的「本地 → 数据库 → Git」三步同步。

---

## 三步同步流程

### Step 1 — 修改本地 skill 文件

编辑 `.claude/skills/<skill-name>/SKILL.md`：

```bash
vim .claude/skills/multica-flow/SKILL.md
```

修改完成后，先本地验证内容无误。

---

### Step 2 — 同步到 Multica 数据库

**使用 multica CLI 更新数据库中的 skill**：

```bash
cd /Users/louis/Downloads/配置任务/ai_project_template

# 获取 skill ID
multica skill list --output json | python3 -c "
import sys, json
skills = json.load(sys.stdin)
for s in skills:
    print(f\"{s['id']}: {s['name']}\")
"

# 更新指定 skill（以 multica-flow 为例）
CONTENT=$(cat .claude/skills/multica-flow/SKILL.md)
multica skill update <SKILL_ID> --content "$CONTENT" --name "multica-flow"
```

**验证同步成功**：

```bash
multica skill get <SKILL_ID> --output json | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('Updated at:', d.get('updated_at'))
"
```

确认 `updated_at` 时间为当前时间。

---

### Step 3 — 提交并推送到 GitHub

```bash
git add -A
git commit -m "feat(skills): update multica-flow with xxx"
git push origin master
```

---

## 批量同步所有 skill

如果修改了多个 skill，可以批量同步：

```bash
cd /Users/louis/Downloads/配置任务/ai_project_template

for skill_file in .claude/skills/*/SKILL.md; do
  skill_name=$(basename $(dirname $skill_file))
  skill_id=$(multica skill list --output json | python3 -c "
import sys, json, os
skills = json.load(sys.stdin)
name = os.environ.get('SKILL_NAME')
[s['id'] for s in skills if s['name'] == name] and print([s['id'] for s in skills if s['name'] == name][0])
" SKILL_NAME="$skill_name")
  
  if [ -n "$skill_id" ]; then
    CONTENT=$(cat "$skill_file")
    multica skill update "$skill_id" --content "$CONTENT" --name "$skill_name"
    echo "$skill_name: synced"
  fi
done

git add -A
git commit -m "feat(skills): batch sync all skills"
git push origin master
```

---

## 关键注意事项

1. **Agent 不读本地文件** — 只改本地 SKILL.md 不更新数据库，Agent 执行时使用的是旧版本 skill
2. **新建 Issue 才生效** — 已分配（running）的 Agent 任务不会重新加载 skill，必须取消旧任务、创建新 Issue 才能使用最新 skill
3. **数据库是唯一的 skill 来源** — multica skill list / multica skill get 查到的才是 Agent 实际使用的版本
4. **Git 提交是备份** — 数据库 skill 是运行时唯一来源，Git 提交是为了团队协作和版本回溯

---

## 验证 Agent 使用的是最新 skill

```bash
# 查看 Agent 最新任务使用的 skill 版本
multica agent tasks <AGENT_ID> --output json | head -50

# 对比数据库中的更新时间
multica skill get <SKILL_ID> --output json | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('updated_at'))
"
```

如果任务启动时间早于 skill 更新时间，说明该任务使用的是旧版本 skill，需要取消重建。
