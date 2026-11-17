# <img src="https://github.com/schemacrawler/SchemaCrawler-Usage/blob/98e442d9a957070d45e87109d5b32d7f17b62927/schemacrawler-website/src/site/resources/images/schemacrawler_logo.png?raw=true" height="100px" width="100px" valign="middle"/> SchemaCrawler Docker Image Attestation Action

> **Note**: Please see the [SchemaCrawler website](https://www.schemacrawler.com/) for more details.

## About

A reusable GitHub Action that creates Docker image provenance attestations using `actions/attest`, publishes them to GitHub and the image registry, publishes immutable image references to workflow summaries, and optionally updates GitHub release notes with image metadata.

## Overview

This action encapsulates Docker image attestation and digest publishing logic, centralizing what would otherwise be duplicated across multiple workflows. It uses the official `actions/attest` action to create SLSA provenance attestations and the GitHub CLI to manage release notes.

### Features

- 🔐 Creates Docker image provenance attestations using `actions/attest`
- 📋 Publishes image digests and attestation status to GitHub Actions step summaries
- 🔗 Generates immutable image references (image@digest) for verification
- 📝 Optionally updates GitHub release notes with image metadata
- 🔄 Idempotent release notes updates with explicit delimiters (safe to rerun without duplication)
- ⚠️ Graceful error handling (attestation failures don't block the workflow)
- 🔐 Proper permission handling and authentication

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| `image-name` | Yes | Registry-qualified Docker image name without a tag or digest (e.g., `docker.io/schemacrawler/schemacrawler`) |
| `digest` | Yes | Multi-platform image digest output from a push operation |
| `publishing-repo` | Yes | GitHub repository path for release notes updates (e.g., `schemacrawler/SchemaCrawler`) |
| `tag-name` | Yes | GitHub release tag name for release notes updates |
| `update-release` | Yes | Boolean indicating whether to update GitHub release notes (`true` or `false`) |

## Outputs

| Output | Description |
|--------|-------------|
| `image-digest` | The image digest value (always available) |
| `immutable-ref` | The full immutable image reference (format: `image@digest`) |
| `attestation-outcome` | The outcome of the attestation step (`success` or `failure`) |
| `attestation-url` | URL to the published attestation (if successful) |

## Permissions

The **calling workflow job** must declare these permissions:

```yaml
permissions:
  id-token: write        # Required for OIDC token used by actions/attest
  attestations: write    # Required for attestation creation
  contents: write        # Required for release notes updates
```

**Important:** These permissions must be declared in the job that calls this action, not in the action metadata itself. GitHub Actions requires explicit permission declarations in workflows.

If you omit a permission:
- Missing `attestations: write` → attestation step fails (continues with `outcome: failure`)
- Missing `contents: write` → release notes update fails (continues with warning)
- Missing `id-token: write` → attestation cannot authenticate (continues with `outcome: failure`)

## Usage Examples

### Migrating to v2.0.0

Version 2 always sets `push-to-registry: true`. Before calling this action, log in to the image registry with credentials that can push to the image repository. Use `docker.io` as the registry for Docker Hub (as recommended by `actions/attest`), not an unqualified image name or `index.docker.io`. Supply the final pushed image digest separately in `digest`.

Artifact metadata storage records are disabled, so no additional `artifact-metadata: write` permission is required. Existing v1 attestations are not automatically copied to the registry.

### Basic usage with attestation and release notes update

```yaml
jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      attestations: write
      contents: write
    steps:
      - name: Log in to Docker Hub
        uses: docker/login-action@v4
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Build and push Docker image
        id: build
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: docker.io/schemacrawler/schemacrawler:${{ github.ref_name }}

      - name: Attest Docker image
        uses: schemacrawler/actions-docker-attest@v2.0.0
        with:
          image-name: docker.io/schemacrawler/schemacrawler
          digest: ${{ steps.build.outputs.digest }}
          publishing-repo: schemacrawler/SchemaCrawler
          tag-name: ${{ github.ref_name }}
          update-release: true
```

### Attestation only (no release notes update)

```yaml
- name: Attest Docker image
  uses: schemacrawler/actions-docker-attest@v2.0.0
  with:
    image-name: docker.io/schemacrawler/schemacrawler
    digest: ${{ steps.build.outputs.digest }}
    publishing-repo: schemacrawler/SchemaCrawler
    tag-name: ${{ github.ref_name }}
    update-release: false
```

### Using outputs in downstream steps

```yaml
- name: Attest Docker image
  id: attest
  uses: schemacrawler/actions-docker-attest@v2.0.0
  with:
    image-name: docker.io/schemacrawler/schemacrawler
    digest: ${{ steps.build.outputs.digest }}
    publishing-repo: schemacrawler/SchemaCrawler
    tag-name: ${{ github.ref_name }}
    update-release: true

- name: Report attestation
  run: |
    echo "Image: ${{ steps.attest.outputs.immutable-ref }}"
    echo "Digest: ${{ steps.attest.outputs.image-digest }}"
    echo "Status: ${{ steps.attest.outputs.attestation-outcome }}"
    if [ "${{ steps.attest.outputs.attestation-outcome }}" = "success" ]; then
      echo "URL: ${{ steps.attest.outputs.attestation-url }}"
    fi
```

### Complete workflow example

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  id-token: write
  contents: write
  attestations: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Log in to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Build and push Docker image
        id: build
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: docker.io/schemacrawler/schemacrawler:${{ github.ref_name }}

      - name: Attest Docker image and update release notes
        uses: schemacrawler/actions-docker-attest@v2.0.0
        with:
          image-name: docker.io/schemacrawler/schemacrawler
          digest: ${{ steps.build.outputs.digest }}
          publishing-repo: schemacrawler/SchemaCrawler
          tag-name: ${{ github.ref_name }}
          update-release: true
```

## How It Works

### Step 1: Create Attestation

The action invokes `actions/attest` (version 4) to create a SLSA provenance attestation for the Docker image.

**Key points:**
- The attestation is published to the GitHub repository where the workflow runs and pushed to the image registry using the existing registry login
- The subject must include the registry and image repository, without a tag; the digest identifies the exact image
- Artifact metadata storage records are disabled
- The `publishing-repo` input does **not** control where attestations are published (that's determined by the workflow's repository)
- `publishing-repo` only affects release notes updates
- If attestation fails (permission issue, transient error), the action continues with `outcome: failure`

### Step 2: Publish to Step Summary

The action publishes to the GitHub Actions step summary:
- Image digest (immutable reference)
- Attestation status and outcome
- Link to attestation (if successful)

This provides immediate, visible feedback in the workflow run UI.

### Step 3: Update Release Notes (Optional)

When `update-release: true`, the action updates the GitHub release specified by `tag-name` in the repository specified by `publishing-repo`.

**Idempotency:**
- Release notes section is delimited with HTML comments: `<!-- docker-image-provenance:start -->` and `<!-- docker-image-provenance:end -->`
- On rerun, the section between delimiters is replaced in place
- Python is used for robust text replacement (avoiding sed interpolation issues)
- If release doesn't exist, a warning is logged and the workflow continues

## Architecture Notes

### Attestation Repository vs. Release Notes Repository

- **Attestation location:** Determined by where the workflow runs. If workflow is in `schemacrawler/SchemaCrawler`, attestations are published there. The `publishing-repo` input cannot redirect this.
- **Release notes location:** Specified by `publishing-repo` input. Can be a different repository from where the workflow runs.

Example: A workflow in `schemacrawler/SchemaCrawler`:
- Creates attestations in `schemacrawler/SchemaCrawler` (not configurable)
- Updates release notes in `schemacrawler/SchemaCrawler` (via `publishing-repo` input)
- Both happen to be the same in this case

### Permissions and Authentication

- `id-token: write` + `attestations: write` → required for `actions/attest`
- `contents: write` + `GH_TOKEN` → required for `gh release edit`
- The action uses `${{ github.token }}` (automatically available in workflows) for release note updates
- Registry push credentials must already be configured, for example by `docker/login-action`; the action reuses that login

### Verification

Replace `<digest>` with the SHA-256 hex value from the workflow summary or release notes:

```sh
# Retrieve the attestation from GitHub
gh attestation verify \
  'oci://docker.io/schemacrawler/schemacrawler@sha256:<digest>' \
  --repo schemacrawler/SchemaCrawler

# Retrieve the attestation from Docker Hub
gh attestation verify \
  'oci://docker.io/schemacrawler/schemacrawler@sha256:<digest>' \
  --repo schemacrawler/SchemaCrawler \
  --bundle-from-oci
```

## Error Handling

The action is designed to fail gracefully:

| Issue | Behavior |
|-------|----------|
| Attestation fails | Recorded as `outcome: failure`; workflow continues |
| Release doesn't exist | Warning logged; workflow continues |
| Release notes update fails | Warning logged; workflow continues |
| Missing `attestations: write` permission | Attestation fails; workflow continues |
| Missing `contents: write` permission | Release update fails; workflow continues |
| Authentication error | Visible in logs; workflow continues |

This design ensures that partial failures (e.g., release not created yet) don't block the overall release process.

## Troubleshooting

### Attestation step shows `outcome: failure` but no error message

**Cause:** Missing `attestations: write` permission.

**Solution:** Add `attestations: write` to the job's `permissions` block.

### Release notes are not being updated

**Cause:** One or more of:
- `update-release: false`
- Missing `contents: write` permission
- Release doesn't exist yet
- `publishing-repo` is incorrect

**Solution:** 
1. Verify `update-release` is `true`
2. Add `contents: write` to permissions
3. Ensure release exists before this step runs
4. Check `publishing-repo` matches the actual repository

### Release notes section appears multiple times

**Cause:** Older implementation used `sed` without delimiters.

**Solution:** Use the current version. If duplicates exist in your releases, manually edit them and remove extras.

## Contributing

Contributions are welcome! Please follow the SchemaCrawler contribution guidelines.

## License

This action is licensed under the MIT License. See [LICENSE](./LICENSE) for details.

## Links

- [SchemaCrawler Website](https://www.schemacrawler.com)
- [GitHub Organization](https://github.com/schemacrawler)
- [actions/attest Documentation](https://github.com/actions/attest)
- [GitHub CLI Documentation](https://cli.github.com)
