import time
import datetime
from datetime import timedelta

print(datetime.date.today()- timedelta(days=14))

for i in range(0,14):
    print(datetime.date.today()- timedelta(days=i))