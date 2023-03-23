conn = Mongo("mongodb://{{mongo_admin_user}}:{{mongo_admin_password}}@127.0.0.1:27017")
db = conn.getDB('admin')
db = db.getSiblingDB('{{database}}');

{% if mode == 'create'%}
db.createUser({
    user: "{{subject}}",
    pwd: "{{auth}}",
    roles: [
        {role: "readWrite", db: "{{subject}}"}
    ]
});
db.nuv_test_collection.insertOne({"message":"Welcome to nuvolaris!"});
{% endif %}

{% if mode == 'delete'%}
db.dropUser("{{subject}}", {w: "majority", wtimeout: 4000});
db.dropDatabase();
{% endif %}