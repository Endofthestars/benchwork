"""Support ``python -m benchwork.cli`` as a compatibility entry point."""

from .main import main


raise SystemExit(main())
