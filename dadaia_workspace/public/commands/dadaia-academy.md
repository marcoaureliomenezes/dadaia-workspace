# /dadaia-academy — Academy tutor

Use this command to study, review, or get help with any course in your dadaia Academy.

## Usage

- `/dadaia-academy` — list existing courses and ask what to study
- `/dadaia-academy <slug>` — open a specific course and start tutoring
- `/dadaia-academy <slug> <topic>` — jump directly to a topic within the course

## Workflow

### No argument

1. Run `dadaia academy list` to discover all courses registered in this workspace.
2. If no courses exist, inform the operator and suggest:
   ```
   dadaia academy modules          # list available modules
   dadaia academy create <name> --module <n>
   ```
3. If courses exist, display the list and ask which one the operator wants to work on.

### With `<slug>`

1. Run `dadaia academy list` to confirm the course exists and retrieve its `course_dir`.
2. If the course does not exist, report `Course '<slug>' not found` and list available courses.
3. Read all files in `.dadaia/academy/<slug>/` as primary learning context:
   - Start with `README.md` for module overview
   - Read numbered content files (`01_*.md`, `02_*.md`, `03_*.md`) for material
   - Read `EXERCISES.md` for practice tasks
   - Read `EXAMPLE.md` for concrete examples
   - Read `REFERENCES.md` for further reading
4. Greet the operator with a brief summary of the module content and ask how to proceed.

### With `<slug> <topic>`

1. Load the course as above.
2. Focus the tutoring session on the requested topic within the module material.

## Tutoring behavior

- Use the course files as the authoritative context for this session — do not improvise curriculum.
- Adapt explanations to the operator's demonstrated level of knowledge.
- Suggest exercises from `EXERCISES.md` proactively.
- When the operator asks questions not covered by the course files, answer from general knowledge but flag that it is outside the module scope.
- Do not call `dadaia academy create`, `delete`, or `update` autonomously — present CLI instructions when state changes are needed:
  ```
  dadaia academy create <name> --module <n>
  dadaia academy update <slug> --module <n>
  dadaia academy delete <slug>
  ```

## Rules

- Always run `dadaia academy list` first to discover the current state — never assume which courses exist.
- Read course files from `.dadaia/academy/<slug>/` — never from the library's `knowledge_basis/` directly.
- Show the `dadaia` commands you run so the operator knows what happened.
- This command is for tutoring only; CLI is the exclusive interface for CRUD operations.
