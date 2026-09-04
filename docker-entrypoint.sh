#!/bin/sh
# Start the two peer departments as their own Agent-to-Agent servers, then the web API.
#
# Riverton and Cedar Hollow each get their own process, their own store and their own AgentCard, so
# Millbrook reaches them over HTTP exactly as it would across organizations. If a peer fails to
# start, the web app still runs and reports the peer as unreachable, which is the honest failure.

set -e

python -m turnout.a2a.server --dept riverton --port 9002 --host 127.0.0.1 &
RIVERTON=$!
python -m turnout.a2a.server --dept cedar --port 9003 --host 127.0.0.1 &
CEDAR=$!

# Give the peers a moment to bind before the first request can arrive.
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
  if python -c "import socket,sys; s=socket.socket(); s.settimeout(0.5); sys.exit(0 if s.connect_ex(('127.0.0.1',9002))==0 else 1)" 2>/dev/null; then
    echo "peers are up"
    break
  fi
  sleep 1
done

trap 'kill $RIVERTON $CEDAR 2>/dev/null || true' TERM INT

exec uvicorn turnout.api.app:app --host 0.0.0.0 --port 8080 --workers 1 --log-level info
