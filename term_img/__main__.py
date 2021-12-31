"""Support for command-line execution using `python -m term-img`"""

import logging as _logging
import sys

from .exit_codes import codes, FAILURE, INTERRUPTED
from . import cli


def main():
    """CLI execution entry-point"""
    from . import logging
    from .tui import main

    # Can't use "term_img", since the logger's level is changed.
    # Otherwise, it would affect children of "term_img".
    logger = _logging.getLogger("term-img")
    logger.setLevel(_logging.INFO)

    try:
        exit_code = cli.main()
    except KeyboardInterrupt:
        logging.log(
            "Session interrupted",
            logger,
            _logging.CRITICAL,
            # If logging has been successfully initialized
            file=logging.VERBOSE is not None,
            # If the TUI was not launched, only print to console if verbosity is enabled
            direct=bool(main.loop or cli.args.verbose or cli.args.debug),
        )
        if cli.args.debug:
            raise
        return INTERRUPTED
    except Exception as e:
        logging.log(
            f"Session not ended successfully: ({type(e).__name__}) {e}",
            logger,
            _logging.CRITICAL,
            # If logging has been successfully initialized
            file=logging.VERBOSE is not None,
        )
        if cli.args.debug:
            raise
        return FAILURE
    else:
        logger.info(f"Session ended with return-code {exit_code} ({codes[exit_code]})")
        return exit_code


if __name__ == "__main__":
    sys.exit(main())
