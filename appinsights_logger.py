"""
Azure Application Insights Logger
"""

"""
Copyright 2022 Alexander Kuemmel

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os
import sys
import yaml
import typer
import logging
import logging.config
from enum import Enum
from opencensus.ext.azure.log_exporter import (
    AzureLogHandler,
    AzureEventHandler,
    Envelope,
)
from pathlib import Path
from typing import Optional, List
from pprint import pformat

logging.basicConfig(level=logging.ERROR)
int_log: logging.Logger = None
ai_logger: logging.Logger = None
ai_logger_name: str = os.getenv("APPINSIGHTS_LOGGER_NAME") or sys.argv[0]
app_config: dict = {}


class LogLevel(str, Enum):
    critical = "critical"
    error = "error"
    warning = "warning"
    info = "info"
    debug = "debug"


def telemetry_processor(envelope: Envelope) -> bool:
    int_log.debug("Executing Application Insights telemetry processor")
    msg_wrap = app_config.get("message_envelope")
    if msg_wrap is None:
        int_log.debug("No message wrap found in config, skipping processor.")
        return True
    msg_wrap_tags = msg_wrap.get("tags")
    if msg_wrap_tags is not None:
        int_log.debug("Merging config tags override into envelope.")
        envelope.tags.update(msg_wrap_tags)
    int_log.debug("Final message envelope\n" + pformat(envelope, indent=2))
    return True


def init_ai_logger(app_name: str, config: dict):
    global ai_logger
    logging.config.dictConfig(config)
    ai_logger = logging.getLogger(app_name)

    if ai_logger.hasHandlers():

        event_handlers = [h for h in ai_logger.handlers if h.name == "event"]
        if len(event_handlers) == 1:
            event_handler: AzureEventHandler = event_handlers.pop()
            event_handler.add_telemetry_processor(telemetry_processor)
        elif len(event_handlers) > 1:
            raise RuntimeError("More than one Application Insights Event handler found")

        trace_handlers = [h for h in ai_logger.handlers if h.name == "trace"]
        if len(trace_handlers) == 1:
            trace_handler: AzureLogHandler = trace_handlers.pop()
            trace_handler.add_telemetry_processor(telemetry_processor)
        elif len(trace_handlers) > 1:
            raise RuntimeError("More than one Application Insights Trace handler found")


def main(
    config: Path = typer.Option(
        Path("appinsights_logconfig.yml"),
        "--config",
        "-c",
        readable=True,
        help="Configuration file path.",
    ),
    ai_logger_name: str = typer.Option(
        ai_logger_name,
        "--app",
        "-a",
        help="Application Insights Logger instance name. Needs to coincide within logger config!",
    ),
    level: LogLevel = typer.Option(
        "info", "--level", "-l", help="Log Level for submitted message."
    ),
    msg: Optional[str] = typer.Option(
        ..., "--message", "-m", help="Log Message to submit."
    ),
    tag: Optional[List[str]] = typer.Option(
        None,
        "--tag",
        "-t",
        help='Custom tag, multiple invocations allowed. Check dist config for available values. [format: "key=value"]',
    ),
    prop: Optional[List[str]] = typer.Option(
        None,
        "--property",
        "-p",
        help='Custom dimension property, multiple invocations allowed. [format: "key=value"]',
    ),
    verbosity: int = typer.Option(
        0,
        "-v",
        count=True,
        show_default=False,
        help="Verbosity level, increased by multiple use.",
    ),
):
    global int_log, app_config
    app_name = ai_logger_name
    int_log = logging.getLogger()
    app_config = yaml.safe_load(config.read_text())
    init_ai_logger(app_name=app_name, config=app_config.get("logging_config"))

    if verbosity > 2:
        int_log.setLevel(logging.DEBUG)
    elif verbosity > 1:
        int_log.setLevel(logging.INFO)
    elif verbosity > 0:
        int_log.setLevel(logging.WARNING)

    if tag is not None:
        int_log.debug("Processing user provided tags.")
        tag.sort()
        tags_override = {}
        for label in tag:
            tag_parts = [p for p in label.split("=") if p.strip()]
            if len(tag_parts) == 1:
                int_log.warning(f"Missing equal sign in tag [{label}], skipping.")
                continue
            tags_override.update({tag_parts[0]: tag_parts[1]})
        if len(tags_override) > 0:
            int_log.debug("Updating tags with overrides in app config.")
            msg_env = app_config.get("message_envelope", {})
            msg_env_tags = msg_env.get("tags", {})
            msg_env_tags.update(tags_override)
            msg_env.update(dict(tags=msg_env_tags))
            app_config.update(dict(message_envelope=msg_env))

    custom_dimensions = {}
    if prop is not None:
        int_log.debug("Processing user provided properties.")
        prop.sort()
        for label in prop:
            property_parts = [p for p in label.split("=") if p.strip()]
            if len(property_parts) == 1:
                int_log.warning(f"Missing equal sign in property [{label}], skipping.")
                continue
            custom_dimensions.update({property_parts[0]: property_parts[1]})

    int_log.info("Logger message processing")
    if msg is None:
        sys.exit(0)
    ai_log = ai_logger.debug
    if level is LogLevel.info:
        ai_log = ai_logger.info
    elif level is LogLevel.warning:
        ai_log = ai_logger.warning
    elif level is LogLevel.critical:
        ai_log = ai_logger.critical
    elif level is LogLevel.error:
        ai_log = ai_logger.error

    custom_payload = dict(custom_dimensions=custom_dimensions)
    ai_log(msg, extra=custom_payload)

    int_log.info("Logger done")


if __name__ == "__main__":
    typer.run(main)
