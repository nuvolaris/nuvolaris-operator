db = db.getSiblingDB('franztt');

db.createUser({
    user: "franztt",
    pwd: "dadadasdaasgdadgagdadakj",
    roles: [
        {role: "readWrite", db: "franztt"}
    ]
});

db.nuv_test_collection.insertOne({"message":"Welcome to nuvolaris!"})