
## Server setup
```
sudo apt-get update
sudo apt-get -y install python3-pip
sudo apt-get install  python3-dev libpq-dev
sudo apt-get install libmysqlclient-dev

wget -P /tmp https://repo.anaconda.com/archive/Anaconda3-2020.02-Linux-x86_64.sh
bash /tmp/Anaconda3-2020.02-Linux-x86_64.sh
press yes for all
source ~/.bashrc
conda create -n tr python=3.8
conda activate tr


pip3 install mysqlclient


pip3 install rx
pip3 install requests
pip3 install fyers-apiv2
pip3 install python-socketio
pip install aiohttp

pip install aiohttp_cors
pip install -U selenium #4.1.3
pip install sqlalchemy
pip install matplotlib

pip install -U kaleido
pip install plotly
pip install mplfinance
pip install PyPDF2
pip install lxml
pip install apscheduler
pip install bs4

python3 -m pip install Django
pip install djangorestframework
pip install django-cors-headers
python3 -m pip install PyMySQL
pip3 install psutil
pip install py_vollib
pip install py_vollib_vectorized
pip install djangorestframework-simplejwt

pip install pyEX
pip install truedata_ws
pip install numba

wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install

conda install -c conda-forge ta-lib

pip install aiohttp_cors
pip install python-socketio
pip3 install --upgrade diskcache
pip install graphviz



https://github.com/mrjbq7/ta-lib

```

Chrome Instalation
```
cd /home/ubuntu 
    1. wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    2. sudo apt-get -y update
    3. sudo apt-get install gconf-service
    4. sudo dpkg -i google-chrome-stable_current_amd64.deb
    In case, It didn't work smoothly, Use this command and repeat steps 3 and 4 :
    1. sudo apt --fix-broken install

google-chrome-stable --version
Ans: Google Chrome 99.0.4844.51

based on version download chrome driver
wget https://chromedriver.storage.googleapis.com/99.0.4844.51/chromedriver_linux64.zip
sudo apt install unzip

sudo apt-get install libnss3 
sudo apt-get install -y chromium-browser   #check if this is required
unzip chromedriver_linux64.zip 
```
## Run Django server
```
python3 manage.py runserver 0.0.0.0:8000 --noreload
migrate
python3 manage.py migrate
run
nohup python3 manage.py runserver 0.0.0.0:8000
```
## NGINX setup
```
sudo apt-get update
sudo apt-get install nginx
sudo ufw app list
sudo ufw allow 'Nginx HTTP'
sudo ufw status
systemctl status nginx

->Reference - https://www.digitalocean.com/community/tutorials/how-to-install-nginx-on-ubuntu-16-04
```

##Redirect NGINX
```
sudo snap install core; 
sudo snap refresh core 
sudo snap install --classic certbot 
sudo ln -s /snap/bin/certbot /usr/bin/certbot
sudo certbot --nginx -d api.niftybull.in

sudo certbot renew --dry-run  
test by going to url : https://api.niftybull.in/

edit /etc/nginx/sites-available/default to add the following (path of location /static and location /media depends on actual folder path)

location / {

       proxy_pass http://0.0.0.0:8000;

       proxy_connect_timeout 360s; 
       proxy_read_timeout 360s;

       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";

       proxy_redirect     off;
       proxy_set_header   Host $host;
       proxy_set_header   X-Real-IP $remote_addr;
       proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header   X-Forwarded-Host $server_name;

   }
-- restart nginx server with folliwng command -- sudo systemctl restart nginx

----- full config file for reference (removed unncessary part) --- 
server {
   server_name api.niftybull.in;
   location /static {
       alias /home/ubuntu/synapses_phase_3/synapses/static-root;
   }

   location /media {
       alias /home/ubuntu/synapses_phase_3/synapses/media;
   }
    location / {
       proxy_pass http://0.0.0.0:8000;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";

       proxy_redirect     off;
       proxy_set_header   Host $host;
       proxy_set_header   X-Real-IP $remote_addr;
       proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header   X-Forwarded-Host $server_name;

   }
  listen [::]:443 ssl ipv6only=on; # managed by Certbot
  listen 443 ssl; # managed by Certbot
  ssl_certificate /etc/letsencrypt/live/api.niftybull.in/fullchain.pem; # managed by Certbot
  ssl_certificate_key /etc/letsencrypt/live/api.niftybull.in/privkey.pem; # managed by Certbot
  include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
  ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}

server { 
  if ($host = api.niftybull.in) { 
      return 301 https://$host$request_uri; 
    } # managed by Certbot
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name api.niftybull.in;
    return 404; # managed by Certbot
} 
sudo systemctl restart nginx


```



##run socket
```
cd tr/market
python run_website_server.py

https://www1.nseindia.com/products/content/derivatives/equities/historical_fo.htm
https://medium.com/@kevin.michael.horan/scheduling-tasks-in-django-with-the-advanced-python-scheduler-663f17e868e6
```
## Run sequence 
```
1. python download_historical_data.py  -- download tick data
2. python calculate_historical_measures.py -- fill in profile data
3.  

```


```
=======
For pkg-config to find mysql-client you may need to set:
  export PKG_CONFIG_PATH="/opt/homebrew/opt/mysql-client/lib/pkgconfig"

https://stackoverflow.com/questions/67420897/cannot-connect-django-to-existing-mysql-database-on-m1-mac
codesign --force --deep --sign - /Applications/DBeaver.app
```
```
Download historical data
python download_hiostorical_data.py

calculate historical measures
python calculate_historical_measures.py

Backtest with socket

local_feed.py
back_test_client.py
hist_socket_server.py

```

https://ip-ranges.amazonaws.com/ip-ranges.json


## True data
```
pip install truedata_ws


```

## TOTP
```
pip install pyotp

```

### Simulate live environment 

```
1. python run_website_server.py
This will launch websockets which can be used by frontend for live data and option data 
2. python run_test_fetcher.py 
This will send live data to socket server for forwarding
2. python algo_client.py 
This will send strategy signals to socket server for forwarding to client
```

### Tensor flow
```
conda install -c apple tensorflow-deps




pymc3 3.11.5
path modelling 
https://github.com/patrickzib/SFA
https://stackoverflow.com/questions/59679629/template-matching-for-candlestick-ohlc-data-in-python
```


### execute service
```
cd forte
python servers/run_oms_server.py
python servers/run_website_server.py
python servers/run_test_fetcher.py

python market/manage.py runserver --norealod
or cd forte/market
python manage.py runserver --noreload

```

### Backtest

```
python backtest/strategy_test.py strat_config=default.json
python work_in_prog/ml.py

option data : option_data
key levels : key_levels
```

