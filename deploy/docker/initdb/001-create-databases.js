// Initializes Mortimer and Alfred databases with dedicated users.
// This script runs automatically via the MongoDB docker entrypoint.

(function () {
  function getenv(key, defaultValue) {
    return (typeof process !== "undefined" && process.env[key]) || defaultValue;
  }

  function ensureUser(db, username, password, roles) {
    if (!username || !password) {
      print(`Skipping user creation for database ${db.getName()} (missing credentials).`);
      return;
    }

    if (db.getUser(username)) {
      print(`User ${username} already exists in ${db.getName()}.`);
      return;
    }

    db.createUser({ user: username, pwd: password, roles: roles });
    print(`Created user ${username} in ${db.getName()}.`);
  }

  const mortimerDbName = getenv("MONGO_INITDB_DATABASE", "mortimer");
  const mortimerUser = getenv("MORTIMER_MONGO_USERNAME", "mortimer_app");
  const mortimerPassword = getenv("MORTIMER_MONGO_PASSWORD", "changeMeToo!");
  const alfredDbName = getenv("ALFRED_DB_NAME", "alfred");

  const mortimerDb = db.getSiblingDB(mortimerDbName);
  ensureUser(mortimerDb, mortimerUser, mortimerPassword, [
    { role: "readWrite", db: mortimerDbName },
    { role: "userAdmin", db: alfredDbName },
    { role: "read", db: alfredDbName },
  ]);

  print("MongoDB initialization script finished.");
})();
