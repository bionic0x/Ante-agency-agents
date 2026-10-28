"""Strategy commands, in the order of the method (Marco XIII) followed by its controls."""
from ante.strategy.commands import (ach, cause, close, cohere, decide, focus, frame, map, options, pathology,
                                   react, selftest, watch)

ORDER = (frame, map, cause, focus, options, react, ach, watch, close, cohere, pathology, decide, selftest)
COMMANDS = {module.COMMAND.name: module.COMMAND for module in ORDER}
