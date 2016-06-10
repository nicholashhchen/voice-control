
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import apiai
import pyaudio
import time
import json
import requests
from os.path import join, dirname
from dotenv import load_dotenv

CHUNK = 512
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 2

# Load API keys from .env file:
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)
CLIENT_ACCESS_TOKEN = os.environ.get("APIAI_TOKEN")
SUBSCRIPTION_KEY = os.environ.get("APIAI_KEY")
SHOPIFY_KEY = os.environ.get("SHOPIFY_KEY")
SHOPIFY_PASS = os.environ.get("SHOPIFY_PASS")
SHOP_URL = "jamie-ds-emporium.myshopify.com"

BASE_URL = "https://%s:%s@%s/admin" % (SHOPIFY_KEY, SHOPIFY_PASS, SHOP_URL)
DEBUG = False

def main():
    evaluate_intent = False
    oldtime = None

    def callback(in_data, frame_count, time_info, status):
        frames, data = resampler.resample(in_data, frame_count)
        state = vad.processFrame(frames)
        request.send(data)

        if (state == 1):
            return in_data, pyaudio.paContinue
        else:
            return in_data, pyaudio.paComplete

    ai = apiai.ApiAI(CLIENT_ACCESS_TOKEN, SUBSCRIPTION_KEY)
    #os.system("say -v Karen \"Hi, I'm Karen. How can I help? \"")

    while True:

        if DEBUG: # text input
            request = ai.text_request()
            request.query = raw_input("How can I help? ")

        else: # voice input
            resampler = apiai.Resampler(source_samplerate=RATE)
            vad = apiai.VAD()

            request = ai.voice_request()
            p = pyaudio.PyAudio()
            stream = p.open(format=FORMAT,
                            channels=CHANNELS,
                            rate=RATE,
                            input=True,
                            output=False,
                            frames_per_buffer=CHUNK,
                            stream_callback=callback)
            stream.start_stream()

            print ("Say!")

            if oldtime is not None:
                if time.time() - oldtime > 10:
                    evaluate_intent = False

            try:
                while stream.is_active():
                    time.sleep(0.1)
            except Exception:
                os.system("say Sorry can you repeat that?")
                raise e
            except KeyboardInterrupt:
                pass

            stream.stop_stream()
            stream.close()
            p.terminate()

        print ("Wait for response...")
        response = request.getresponse()

        s = response.read()
        print s
        json_obj = json.loads(s)

        message = ""

        try:
            intent = json_obj['result']['metadata']['intentName']
            params = json_obj['result']['parameters']

            print intent
            print params

            if intent == 'start':
                evaluate_intent = True
                print "starting the conversation"
                oldtime = time.time()

            elif evaluate_intent == True:
                if intent == 'customer-lookup':
                    first_name = params['customer-name']['first-name']
                    last_name = params['customer-name']['last-name']
                    customer_info = params['customer-info']
                    r = requests.get ("%s/customers/search.json?query=%s+%s" % (BASE_URL, first_name, last_name))
                    customer_data = json.loads(r.content)['customers'][0]

                    if customer_info == 'address':
                        answer = customer_data['default_address']['address1']
                    elif customer_info == 'city':
                        answer = customer_data['default_address']['city']
                    elif customer_info == 'phone-number':
                        answer = str(customer_data['default_address']['phone'])
                    elif customer_info == 'country':
                        answer = customer_data['default_address']['country']
                    elif customer_info == 'order-total':
                        answer = str(customer_data['total_spent']) + 'dollars'
                    elif customer_info == 'email':
                        answer = customer_data['email']

                    message = "The %s for %s %s is %s" % (customer_info, first_name, last_name, answer)

                elif intent == 'order-information':
                    number = params['order-number']

                    if number is not None:
                        r = requests.get("%s/orders/%d.json" % (BASE_URL, number))

                    # WIP

                elif intent == 'modify-order':
                    # TBD: Allow user to provide order 'name' instead of number
                    number = int(params['order-number'])
                    action = params['order-action']

                    if number is not None:
                        prefix = "%s/orders/%d"  % (BASE_URL, number)

                        if action == 'cancel' or action == 'close':
                            r = requests.post('%s/%s.json' % (prefix, action), data={})

                            if r.status_code == 200:
                                if action == 'cancel':
                                    message = "Cancelled order number %d" % number
                                elif action == 'close':
                                    message = "Closed order number %d" % number
                            else:
                                message = "Couldn't perform that action on order %d" % number

                        elif action == 'delete':
                            r = requests.delete('%s.json' % prefix)

                            if r.status_code == 200:
                                message = "Deleted order %d" % number
                            else:
                                message = "Couldn't delete order %d" % number

                        elif action == 'note':
                            note = "This note is a test!"
                            payload = {"order": {"note": note}}
                            r = requests.put('%s.json' % prefix, json=payload)

                            if r.status_code == 200:
                                message = "Added note %s to order %s" % (note, number)
                            else:
                                message = "I wasn't able to find that order."

                        # elif action == 'fulfill':
                            # WIP

                        # elif action == 'create':
                            # WIP

                elif intent == 'fulfillment-count':
                    state = params['fulfillment-state']

                    if state is not None:
                        r = requests.get ("%s/orders/count.json?fulfillment_status=%s" % (BASE_URL, state))
                        count = json.loads(r.content)['count']

                        if state == 'shipped':
                            message = "%d orders have been shipped" % count
                        elif state == 'unshipped':
                            message = "%d orders have not been shipped" % count
                        else:
                            message = "%d orders have %s status" % (count, action)

                elif intent == 'order-history-period':
                    period = params['date-period']

                    start_date = period.split('/')[0].replace('/', '-') + "T00:00:00-05:00"
                    end_date = period.split('/')[1].replace('/', '-') + "T23:59:59-05:00"

                    r = requests.get ("%s/orders/count.json?created_at_min=%s&created_at_max=%s" % (BASE_URL, start_date, end_date))
                    count = json.loads (r.content)['count']

                    message = "There were %d orders during that period." % count


                elif intent == 'order-history-date':
                    date = params['date']
                    request_date_min = date+"T00:00:00-05:00"
                    request_date_max = date+"T23:59:59-05:00"

                    r = requests.get ("%s/orders/count.json?created_at_min=%s&created_at_max=%s" % (BASE_URL, request_date_min, request_date_max))
                    count = json.loads (r.content)['count']

                    message = "There were %d orders on that day." % count


                elif intent == 'product-information':
                    product = params['product']
                    r = requests.get("%s/products.json?title=%s" % (BASE_URL, product))
                    try:
                        prod_inventory = json.loads(r.content)['products'][0]['variants'][0]['inventory_quantity']
                        message = "You have %s %s remaining in inventory" % (prod_inventory, product)
                    except:
                        message = "Could not find information for %s" % product
                else:
                    print "Didn't evaluate intent."

                evaluate_intent = False

        except KeyError:
            evaluate_intent = False
            message = "I'm not sure what you mean."

        if message != "":
            print message   
            os.system("say -v karen \"%s.\"" % message)

        time.sleep(0.5)

if __name__ == '__main__':
    main()
