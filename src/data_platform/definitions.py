import os
import subprocess
from collections.abc import Sequence

from dagster import (
    AssetExecutionContext,
    AssetSelection,
    Definitions,
    MaterializeResult,
    ScheduleDefinition,
    asset,
    define_asset_job,
)
from data_platform.config import SourceConfig, default_source_config_path, load_source_configs
from data_platform.connectors import build_connector


def _build_ingestion_asset(source_config: SourceConfig):
    @asset(
        name=f"ingest_{source_config.name}",
        group_name="ingestion",
        description=(
            f"Load the {source_config.name} {source_config.type} source into "
            f"ClickHouse dataset {source_config.dataset_name} with dlt."
        ),
        tags={"connector": source_config.type, "dataset": source_config.dataset_name},
    )
    def ingestion_asset(context: AssetExecutionContext) -> MaterializeResult:
        context.log.info("Starting source %s", source_config.name)
        load_info = build_connector(source_config).run()
        context.log.info("%s", load_info)
        return MaterializeResult(
            metadata={
                "source": source_config.name,
                "connector": source_config.type,
                "dataset": source_config.dataset_name,
                "load_info": str(load_info),
            }
        )

    return ingestion_asset


def _build_dbt_asset(ingestion_assets: Sequence[object]):
    dependency_keys = [next(iter(asset_definition.keys)) for asset_definition in ingestion_assets]

    @asset(
        name="dbt_build",
        group_name="transformation",
        deps=dependency_keys,
        description="Build and test the ClickHouse transformation layer with dbt.",
    )
    def dbt_build(context: AssetExecutionContext) -> MaterializeResult:
        project_dir = os.getenv("DBT_PROJECT_DIR", "/opt/data-platform/dbt")
        profiles_dir = os.getenv("DBT_PROFILES_DIR", project_dir)
        target = os.getenv("DBT_TARGET", "local")
        command = [
            "dbt",
            "build",
            "--project-dir",
            project_dir,
            "--profiles-dir",
            profiles_dir,
            "--target",
            target,
        ]
        context.log.info("Running: %s", " ".join(command))
        completed = subprocess.run(command, check=True, text=True, capture_output=True)
        context.log.info("%s", completed.stdout)
        return MaterializeResult(metadata={"target": target, "output": completed.stdout[-4000:]})

    return dbt_build


source_configs = [
    config for config in load_source_configs(default_source_config_path()) if config.enabled
]
ingestion_assets = [_build_ingestion_asset(config) for config in source_configs]
dbt_asset = _build_dbt_asset(ingestion_assets)
all_assets_job = define_asset_job("all_assets", selection=AssetSelection.all())
daily_schedule = ScheduleDefinition(
    job=all_assets_job,
    cron_schedule=os.getenv("PLATFORM_SCHEDULE_CRON", "0 5 * * *"),
    execution_timezone=os.getenv("PLATFORM_TIMEZONE", "UTC"),
)

defs = Definitions(
    assets=[*ingestion_assets, dbt_asset],
    jobs=[all_assets_job],
    schedules=[daily_schedule],
)
