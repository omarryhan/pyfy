#!/bin/bash

if [ "$PYFY_INTEGRATION_TEST_SNYC" = true ] && [ "$PYFY_INTEGRATION_TEST_ASNYC" = true ]; then
    py.test -vs --no-print-logs --cov pyfy/ tests/test_units/ tests/test_integration/;
elif [ "$PYFY_INTEGRATION_TEST_SNYC" = true ] && [ "$PYFY_INTEGRATION_TEST_ASNYC" != true ]; then
    py.test -vs --no-print-logs --cov pyfy/ tests/test_units/ tests/test_integration/test_sync;
elif [ "$PYFY_INTEGRATION_TEST_SNYC" != true ] && [ "$PYFY_INTEGRATION_TEST_ASNYC" = true ]; then
    py.test -vs --no-print-logs --cov pyfy/ tests/test_units/ tests/test_integration/test_async;
elif [ "$PYFY_INTEGRATION_TEST_SNYC" != true ] && [ "$PYFY_INTEGRATION_TEST_ASNYC" != true ]; then
    py.test -vs --no-print-logs --cov pyfy/ tests/test_units/;
fi