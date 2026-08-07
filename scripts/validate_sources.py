from __future__ import annotations

import argparse

from data_platform.config import load_source_configs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate connector YAML and environment references"
    )
    parser.add_argument("path", nargs="?", default="config/sources.yml")
    args = parser.parse_args()

    sources = load_source_configs(args.path)
    enabled = [source.name for source in sources if source.enabled]
    print(f"Valid configuration: {len(sources)} sources, {len(enabled)} enabled")
    if enabled:
        print(f"Enabled: {', '.join(enabled)}")


if __name__ == "__main__":
    main()
