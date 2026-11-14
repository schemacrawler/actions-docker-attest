# <img src="https://github.com/schemacrawler/SchemaCrawler-Usage/blob/98e442d9a957070d45e87109d5b32d7f17b62927/schemacrawler-website/src/site/resources/images/schemacrawler_logo.png?raw=true" height="100px" width="100px" valign="middle"/> SchemaCrawler Docker Image Attestation Action

> **Note**: Please see the [SchemaCrawler website](https://www.schemacrawler.com/) for more details.

## About

A reusable GitHub Action that creates Docker image provenance attestations, publishes immutable image references to workflow summaries, and optionally updates GitHub release notes with image metadata.

## Overview

This action encapsulates Docker image attestation and digest publishing logic, centralizing what would otherwise be duplicated across multiple workflows. It leverages the `actions/attest` action to create SLSA provenance attestations and the GitHub CLI to manage release notes.

### Features

- 🔐 Creates Docker image provenance attestations using `actions/attest`
- 📋 Publishes image digests and attestation status to GitHub Actions step summaries
- 🔗 Generates immutable image references (image@digest) for verification
- 📝 Optionally updates GitHub release notes with image metadata
- 🔄 Idempotent release notes updates (safe to rerun without duplication)
- ⚠️ Graceful error handling (attestation failures don't block the workflow)

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| `image-name` | Yes | Fully qualified Docker image name (e.g., `index.docker.io/schemacrawler/schemacrawler`) |
| `digest` | Yes | Multi-platform image digest output from a push operation |
| `publishing-repo` | Yes | GitHub repository path where attestations are published (e.g., `schemacrawler/SchemaCrawler`) |
| `tag-name` | Yes | GitHub release tag name for release notes updates |
| `update-release` | Yes | Boolean indicating whether to update GitHub release notes (`true` or `false`) |

## Outputs

| Output | Description |
|--------|-------------|
| `image-digest` | The image digest value |
| `immutable-ref` | The full immutable image reference (format: `image@digest`) |
| `attestation-outcome` | The outcome of the attestation step (`success` or `failure`) |

## Permissions

The calling workflow must include the following permissions:

```yaml
permissions:
  id-token: write        # Required by actions/attest
  contents: write        # Required for release notes updates
  attestations: write    # Required for attestation creation
```

## Usage Examples

### Basic usage with attestation and release notes update

```yaml
- name: Attest Docker image
  uses: schemacrawler/actions-docker-attest@v1
  with:
    image-name: index.docker.io/schemacrawler/schemacrawler
    digest: ${{ steps.build.outputs.digest }}
    publishing-repo: schemacrawler/SchemaCrawler
    tag-name: ${{ github.ref_name }}
    update-release: true
```

### Attestation only (no release notes update)

```yaml
- name: Attest Docker image
  uses: schemacrawler/actions-docker-attest@v1
  with:
    image-name: index.docker.io/schemacrawler/schemacrawler
    digest: ${{ steps.build.outputs.digest }}
    publishing-repo: schemacrawler/SchemaCrawler
    tag-name: ${{ github.ref_name }}
    update-release: false
```

### Using outputs in downstream steps

```yaml
- name: Attest Docker image
  id: attest
  uses: schemacrawler/actions-docker-attest@v1
  with:
    image-name: index.docker.io/schemacrawler/schemacrawler
    digest: ${{ steps.build.outputs.digest }}
    publishing-repo: schemacrawler/SchemaCrawler
    tag-name: ${{ github.ref_name }}
    update-release: true

- name: Notify on attestation outcome
  run: |
    echo "Image: ${{ steps.attest.outputs.immutable-ref }}"
    echo "Status: ${{ steps.attest.outputs.attestation-outcome }}"
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

      - name: Build and push Docker image
        id: build
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: index.docker.io/schemacrawler/schemacrawler:${{ github.ref_name }}

      - name: Attest Docker image
        uses: schemacrawler/actions-docker-attest@v1
        with:
          image-name: index.docker.io/schemacrawler/schemacrawler
          digest: ${{ steps.build.outputs.digest }}
          publishing-repo: schemacrawler/SchemaCrawler
          tag-name: ${{ github.ref_name }}
          update-release: true
```

## How It Works

### Step 1: Create Attestation

The action calls `actions/attest` with a pinned SHA to create a provenance attestation for the Docker image. This attestation is published to the GitHub Actions attestations store and can be verified using the `gh attestation verify` command.

If attestation fails (due to permission issues or platform errors), the action continues with a recorded failure status rather than failing the entire workflow.

### Step 2: Publish to Step Summary

The action publishes the following information to the GitHub Actions step summary:
- Image digest
- Immutable image reference (image@digest)
- Attestation status (success or failure)
- Link to view attestations (if successful)

This summary is displayed in the workflow run details and provides immediate visibility into the attestation outcome.

### Step 3: Update Release Notes (Optional)

When `update-release` is `true`, the action updates the GitHub release notes for the specified tag with a "Docker Image Provenance" section containing:
- The immutable image reference
- The image digest
- A link to view attestations

The update is idempotent: if the section already exists, it is replaced rather than duplicated. This allows safe reruns of the workflow without corrupting release notes.

## Error Handling

The action is designed to be resilient:

- **Attestation failure**: Recorded as a failure outcome, but the workflow continues. This handles transient issues and permission problems.
- **Release not found**: A warning is logged, but the workflow continues. This is common during initial tag creation.
- **Missing permissions**: Individual steps fail gracefully. If `contents: write` is missing, release notes updates are skipped; if `attestations: write` is missing, attestation is skipped.

## Troubleshooting

### Attestation step fails with permission error

**Issue:** The `update-release` step logs permission errors.

**Solution:** Ensure the workflow has the `attestations: write` permission in the `permissions` section.

### Release notes are not being updated

**Issue:** The release notes section does not appear after the workflow runs.

**Solution:** Check that:
1. `update-release` is set to `true`
2. The workflow has `contents: write` permission
3. A GitHub release exists for the specified `tag-name`

### Duplicate sections in release notes

**Issue:** Multiple "Docker Image Provenance" sections appear after multiple workflow runs.

**Solution:** This should not happen with the current implementation. If it does, manually edit the release notes to remove duplicates and ensure only one section remains at the top.

## Contributing

Contributions are welcome! Please follow the SchemaCrawler contribution guidelines when submitting pull requests.

## License

This action is licensed under the MIT License. See [LICENSE](./LICENSE) for details.

## Links

- [SchemaCrawler Website](https://www.schemacrawler.com)
- [GitHub Organization](https://github.com/schemacrawler)
- [actions/attest Documentation](https://github.com/actions/attest)
