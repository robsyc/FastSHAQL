# justfile for fastshaql — standardized toolchain and workflows.

set dotenv-load := false

# list the recipes in curated order
default:
	@just --list --unsorted

# sync the environment to uv.lock (extras, dev group, workspace packages)
[group('setup')]
sync:
	uv sync --all-extras --all-groups --all-packages

# install git hooks (lefthook, pinned in the dev group)
[group('setup')]
hooks:
	uv run lefthook install

# upgrade locked dependencies to their latest compatible versions
[group('setup')]
upgrade:
	uv lock --upgrade
	just sync

# verify uv.lock matches pyproject.toml
[group('checks')]
lock-check:
	uv lock --check

# check formatting with ruff
[group('checks')]
format:
	uv run ruff format --check .

# lint with ruff
[group('checks')]
lint:
	uv run ruff check .

# preview unstable lint rules (advisory, never blocks)
[group('checks')]
lint-preview:
	uv run ruff check --preview --exit-zero .

# typecheck with ty
[group('checks')]
typecheck:
	uv run --all-packages ty check src tests demo

# check cognitive complexity against the snapshot baseline (complexipy)
[group('checks')]
complexity:
	uv run complexipy --plain --failed

# recreate the complexity snapshot after an intentional change
[group('checks')]
complexity-update:
	uv run complexipy --snapshot-create --quiet

# check module boundaries against tach.toml (stages → root ∥ core → adapters/stores)
[group('checks')]
architecture:
	uv run tach check

# verify the httpx import guard fails helpfully without the extra (isolated env)
[group('checks')]
import-guard:
	uv run --isolated --no-project --with . python tests/support/import_guard.py

# apply lint, format, and typecheck fixes
[group('checks')]
fix:
	uv run ruff check --fix .
	uv run ruff format .
	uv run --all-packages ty check --fix src tests demo

# run all CI checks
[group('checks')]
ci: format lint typecheck complexity architecture import-guard test-cov
	actionlint

# run the test suite (Docker-dependent evaluation tier excluded)
[group('tests')]
test *args:
	uv run pytest {{args}}

# run the test suite with coverage (gates at 100%)
[group('tests')]
test-cov:
	uv run pytest --cov --cov-report=term-missing

# run the evaluation tier (requires Docker and a GraphDB license, else skipped)
[group('tests')]
eval *args:
	uv run pytest -m evaluation -s {{args}}

# render the evaluation report markdown summary
[group('tests')]
eval-report:
	uv run python tests/support/eval/report.py --render-summary

# mutation testing: run mutmut, then gate on the committed score floor
[group('tests')]
mutate:
	uv run mutmut run
	uv run mutmut export-cicd-stats
	uv run python tests/support/mutation/floor.py

# regenerate the shields endpoint badges into badges/ (needs mutate's stats)
[group('tests')]
badges:
	mkdir -p badges
	uv run pytest -q --cov --cov-report=json:badges/coverage-raw.json
	uv run python -m tests.support.badges

# run the demo server (quickstart fixture by default; args pass through)
[group('demo')]
demo *args:
	uv run --package fastshaql-demo python -m demo.server {{args}}

# smoke-test the quickstart fixture: parse, build, and run every tour query
[group('demo')]
smoke:
	uv run --package fastshaql-demo python -m demo.smoke

# build the sdist and wheel into dist/ (publishable metadata: no uv sources)
[group('release')]
build:
	uv build --no-sources

# smoke-test the built distributions in isolated environments (build first)
[group('release')]
smoke-dist:
	uv run --isolated --no-project --with dist/*.whl demo/smoke.py
	uv run --isolated --no-project --with dist/*.tar.gz demo/smoke.py

# draft the unreleased CHANGELOG.md section + sync CITATION.cff
[group('release')]
changelog:
	@if grep -q "^## \[$(uv version --short)\]" CHANGELOG.md; then echo "changelog: a [$(uv version --short)] section already exists — bump the version first (uv version --bump <part>)"; exit 1; fi
	uvx --from 'git-cliff==2.13.1' git-cliff --unreleased --tag v$(uv version --short) --prepend CHANGELOG.md
	sed -i -e "s/^version: .*/version: $(uv version --short)/" -e "s/^date-released: .*/date-released: \"$(date +%F)\"/" CITATION.cff

# print the CHANGELOG.md section body for VERSION (release notes for a tag)
[group('release')]
release-notes version:
	python3 tests/support/release_notes.py {{version}}

# regenerate the module-dependency diagram in docs/ARCHITECTURE.md
[group('docs')]
module-graph:
	uv run python tests/support/architecture/module_graph.py

# refresh the W3C spec markdown snapshots under docs/references
[group('docs')]
fetch-specs:
	uv run python docs/references/fetch_specs.py
