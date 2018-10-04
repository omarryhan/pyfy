#!/bin/bash
if [ "$PYFY_INTEGRATION_TEST" = true ]; then
    py.test -vs --no-print-logs --cov pyfy/ tests/test_units/ tests/test_integration/;
    #py.test -vs --no-print-logs --cov pyfy/ tests/test_integration/
else
    py.test -vs --no-print-logs --cov pyfy/ tests/test_units/
fi