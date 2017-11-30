#!/bin/csh

pushd "/usr/home/iamOgunyinka/Grace/"
source venv/bin/activate.csh
setenv SECRET_KEY "as6234oeryertertertpsefjest9e6586ds9t056rturentret4nv54taw"
setenv MAIL_USERNAME "graceservr@gmail.com"
setenv MAIL_PASSWORD "d0u3l3_0n_6"

setenv cache_filename "/home/iamOgunyinka/Grace/data/cache"
setenv redis_pass "d3v3l05"
setenv redis_port 6380

pushd EmailBroker
exec gunicorn -w 1 -b 127.0.0.1:8766 email_broker:app
popd
