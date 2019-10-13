# POST
curl -d '{"email":"example@mail.ru", "ticker":"TSLA", "min_price": 250.200, "max_price": 270.232}' -H "Content-Type: application/json" -X POST http://127.0.0.1:5000/subscription
curl -d '{"email":"example@mail.ru", "ticker":"TSLA", "min_price": 250.200}' -H "Content-Type: application/json" -X POST http://127.0.0.1:5000/subscription
curl -d '{"email":"example@mail.ru", "ticker":"TSLA", "max_price": "qwe"}' -H "Content-Type: application/json" -X POST http://127.0.0.1:5000/subscription
curl -d '{"email":"example@mail.ru", "ticker":"TSLA"}' -H "Content-Type: application/json" -X POST http://127.0.0.1:5000/subscription
curl -d '{"email":"example@mail.ru"}' -H "Content-Type: application/json" -X POST http://127.0.0.1:5000/subscription

# DELETE
curl -X DELETE 'http://127.0.0.1:5000/subscription?email=mail@example.com&ticker=TSLA' 
curl -X DELETE 'http://127.0.0.1:5000/subscription?email=mail@example.com'
curl -X DELETE 'http://127.0.0.1:5000/subscription'
