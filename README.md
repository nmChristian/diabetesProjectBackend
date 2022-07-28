# Full stack backend
## Installation
Install all dependencies. In a terminal, this can be done with:
```
python -m pip install -r requirements.txt
```
Then follow this guide to install MongoDB: https://www.mongodb.com/docs/manual/administration/install-community/

When the database is up and running, the script `setup_database.py` can be run. 
Choose `1` to setup some dummy data that can be used for testing (This will take a few minutes). 
It will also automatically setup database indexes and add a doctor user.

The doctor user has credentials `doctor@example.com` and `password1`, and 
patients have credentials `user<i>@example.com` and `password1` where `<i>` is a number between 0 and 999.

When everything is set up, the server can be started by running `start_server.py`.

## API documentation
The APi has been documented using swagger and can be found [here](swagger/openapi.yaml) 
to view the compiled version website like  [https://editor.swagger.io/](https://editor.swagger.io/) can be used.