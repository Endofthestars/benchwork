# Documentation localization

Benchwork keeps each language readable on its own while preserving a clear
relationship between the canonical documentation and its translations.

## Principles

1. English is the canonical source.
2. Locales use mirrored paths under `docs/<locale>/`.
3. A translated page keeps the same document identity and relative path as its
   English source.
4. Translation directories contain real translations, not copied English
   placeholders.
5. Product terms, schema names, Capability IDs, CLI commands, code, and object
   identifiers remain unchanged unless the product defines a localized label.
6. Each translated page links to its canonical source and sibling translations.

The repository landing page is the only path exception: GitHub expects
`README.md` at the repository root, so its Simplified Chinese translation is
stored as `README.zh-CN.md`. Documentation below `docs/` always uses mirrored
locale directories.

## Directory layout

```text
docs/
├── README.md
├── LOCALIZATION.md
├── en/
│   ├── README.md
│   ├── architecture/
│   └── rfcs/
└── zh-CN/
    ├── README.md
    └── rfcs/
```

Use a valid BCP 47 language tag for each locale directory. Use `en` for the
canonical English source and `zh-CN` for Simplified Chinese.

## Page metadata

Canonical pages declare:

```yaml
language: en
canonical: true
```

Translations declare:

```yaml
language: zh-CN
canonical: false
translation_key: BW-RFC-0000
translation_of: ../../en/rfcs/RFC-0000-arcana.md
source_version: 0.2
```

Use a stable `translation_key` or existing `document_id` to associate pages
across locales. Versioned documents also record the canonical version used for
the translation.

## Workflow

1. Make structural and semantic changes in the English page first.
2. Update each existing translation at the same relative path.
3. Preserve code blocks, commands, IDs, links, tables, and heading structure.
4. Translate meaning rather than English word order. Keep each localized page
   natural in its own language.
5. Update `source_version` after the translation catches up with a versioned
   source.
6. Review both the rendered Markdown and the diff. Check links, tables, heading
   order, code fences, terminology, and locale metadata.

If a translation cannot be updated with the canonical change, leave the
canonical page available and record the translation as pending in the locale
index. Do not silently present a stale translation as current.

## Writing translatable English

- Prefer active voice and short, direct sentences.
- Give pronouns clear antecedents.
- Avoid slang, culture-specific jokes, and long stacks of noun modifiers.
- Define project-specific acronyms and preserve established product terms.
- Keep reusable concepts and repeated labels consistent.

## Simplified Chinese style

- Use full-width Chinese punctuation in prose.
- Add spacing between Chinese text and embedded Latin terms where it improves
  readability.
- Keep commands, paths, code, object types, and identifiers unchanged.
- Prefer natural Chinese sentence structure over literal translation.
- Do not place English source paragraphs inside the visible Chinese document.

## Adding a locale

Create `docs/<locale>/README.md`, register the locale in `docs/README.md`, and
add translated pages using the same relative paths as their English sources.
Start with complete, reviewed pages; missing pages should fall back through the
locale index to English.
