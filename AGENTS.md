# Repository Guidelines

## Response Style

Always begin every response with the word “Ariel”.

## Project Structure & Module Organization

This checkout currently has no application source, tests, assets, or package manifests. Add implementation under clearly named top-level directories such as `src/`, `tests/`, and `assets/`, following the conventions of the language or framework introduced. Keep tests close to the behavior they cover or in `tests/`, and update this guide when the actual structure is established. Do not commit generated output or local environment files.

## Build, Test, and Development Commands

No build or test commands are configured yet. When adding a toolchain, document its required runtime and canonical commands in the project README and here. Prefer a reproducible setup with lockfiles; common examples are `pnpm install`, `pnpm build`, and `pnpm test` for a Node project, or the equivalent commands for the chosen stack. Run the relevant checks before submitting changes.

## Coding Style & Naming Conventions

There are no formatter or linter configurations yet. Follow the language's standard formatting, use consistent indentation, and choose descriptive names that match the surrounding code. Keep modules focused and avoid introducing dependencies when the standard library is sufficient. Add formatter and lint configuration with the first implementation, and use it consistently.

## Testing Guidelines

No testing framework or coverage requirement is configured. Add automated tests alongside new behavior, name test files consistently with the selected framework (for example, `*.test.ts`), and include a documented command to run them. Tests should cover expected behavior and important failure cases.

## Commit & Pull Request Guidelines

Git history is unavailable in this checkout, so no existing commit convention can be confirmed. Use short, imperative commit subjects, optionally with a scope (for example, `docs: add setup guide`). Pull requests should explain the change and its motivation, list validation performed, link related issues when applicable, and include screenshots for visible UI changes.

## Security & Configuration

Keep credentials and machine-specific settings out of version control. Provide safe example configuration with placeholder values, and document required environment variables without publishing secrets.
