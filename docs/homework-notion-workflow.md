# Homework Notion Workflow

This file records the standard workflow for Mandarin homework that starts locally and ends in Notion for the teacher.

## Source Of Truth

- Draft homework locally first.
- Review and fix the local draft before publishing.
- Publish the final homework to the Notion database `博丹的作业`.

Local draft location:

- `homework/YYYY-MM-DD-hsk-2.x.md`

Examples:

- `homework/2026-05-02-hsk-2.6.md`
- `新HSK 2.6`

## Local Draft Rules

Keep the local file as the working source while writing and revising.

Homework must stay the student's own work.

- Codex must never solve homework on the student's behalf.
- Codex may help by spotting mistakes, weak wording, typos, or missing items.
- By default, Codex should only hint at mistakes and explain what is wrong.
- Codex should not rewrite answers into final corrected form unless the user explicitly asks for that.
- When checking homework, prefer feedback such as:
  - what line is wrong
  - what kind of mistake it is
  - what to rethink
  - optional answer patterns or grammar cues without giving the final full solution
- If the user wants a final corrected version anyway, treat that as an explicit override rather than the default workflow.

The local draft may include helper notes such as:

- date
- local status
- workflow notes
- source links

Those helper notes are for local work only and should not be published into the final Notion homework page unless they are part of the lesson content.

## Publish Target

Publish into the Notion database:

- `博丹的作业`
- Database URL: `https://www.notion.so/2d3e3cb4edf880b09aeedd8ec38dd568`

Page title rule:

- Use `新HSK 2.x`
- Example: `新HSK 2.6`

Before creating a new page:

1. check whether that lesson already exists in the database
2. if it exists, update the existing page instead of creating a duplicate
3. if it does not exist, create a new page in the database

## Notion Page Style

Match the existing homework pages in `博丹的作业`.

### Section Colors

- Main lesson headings use orange
- Supporting headings use purple
- Filled answers inside drills use red

### Heading Pattern

Use this structure when the lesson content supports it:

```md
## <span color="orange">课文 1</span>
...
### <span color="purple">问题</span>
...
### <span color="purple">练习 2</span>
...
## <span color="orange">课文 2</span>
...
## <span color="orange">综合练习</span>
...
```

### Content Pattern

- Dialogues are written as short speaker lines
- Reading passages are plain paragraph text
- `问题` answers stay on the same line after an arrow: `→`
- Drill answers that fill blanks should be highlighted with red inline spans
- When a two-line exercise needs line breaks inside one numbered item, use `<br>`

Examples:

```md
1. 明天是谁的生日？→ 明天是王一雪女儿的生日。
```

```md
1. A：今天买的苹果<span color="red">很好吃</span>。<br>
   B：我吃了一个，也很好吃。
```

```md
4. A：这是什么？<br>
   B：送你的礼物，快<span color="red">打开</span>看看。
```

## What To Publish

Publish the lesson content itself:

- `课文 1`, `课文 2`, `课文 3`, `课文 4`
- `问题`
- `练习 2`
- `综合练习`
- picture-based completion items when they belong to the homework

Do not publish local-only scaffolding such as:

- `Date:`
- `Status:`
- `Workflow:`
- `Notion source:`
- `Current Notion visibility:`
- `Notion Style Notes`

## Upload Checklist

Before upload:

1. finish the local draft in `homework/`
2. review answers for grammar, wording, and missing items
3. make sure section order matches the lesson
4. remove local-only metadata from the published version

During upload:

1. create or open the page in `博丹的作业`
2. set the page title to `新HSK 2.x`
3. paste the lesson using the Notion style in this file
4. preserve orange, purple, and red emphasis where used

After upload:

1. open the page and verify headings, spacing, and inline answers
2. check that no local-only notes leaked into the page
3. send the teacher the page link with a short polite message

## Suggested Teacher Message

Warm version:

```text
老师您好！我做完了 HSK 2.6 的作业，给您发过来啦。您有时间的时候帮我看看吧，谢谢老师！
```

Then send the Notion page link on the next line.

## Codex Workflow

If using Codex to publish:

1. ask Codex to review the local homework file
2. ask Codex to create or update the Notion page in `博丹的作业`
3. ask Codex to draft the teacher message with the homework link

This keeps the repo as the drafting space and Notion as the teacher-facing final view.
