Do not check this directory in

python3-saml expects

* sp.key      : Private Key
* sp.crt      : Public Cert
* sp\_new.crt : Future Public Cert

Create keys and certs with
`openssl req -new -x509 -days 3652 -nodes -out sp.crt -keyout sp.key`
`openssl req -new -x509 -days 3652 -nodes -out sp_new.crt -keyout sp_new.key`
