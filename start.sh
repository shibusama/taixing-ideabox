#!/bin/sh
pnpm run build && npx serve dist -l ${DEPLOY_RUN_PORT}
