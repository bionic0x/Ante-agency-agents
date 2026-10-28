"""Strategy commands, in the order of the method (Marco XIII) followed by its controls."""
from ante.strategy.commands import (ach, cause, close, cohere, decide, focus, frame, map, nodal, options,
                                   pathology, react, selftest, street, watch)

ORDER = (frame, map, cause, focus, options, react, street, ach, watch, close, cohere, pathology, nodal, decide, selftest)
COMMANDS = {module.COMMAND.name: module.COMMAND for module in ORDER}
