const { MongoClient } = require("mongodb");

const MONGODB_URI = process.env.MONGODB_URI || "";
const MONGODB_DB_NAME = process.env.MONGODB_DB_NAME || "fitplanai";

let client;
let db;

async function connectToDatabase() {
  if (db) {
    return db;
  }

  if (!MONGODB_URI) {
    throw new Error("Missing MONGODB_URI in environment.");
  }

  client = new MongoClient(MONGODB_URI);
  await client.connect();
  db = client.db(MONGODB_DB_NAME);
  await db.command({ ping: 1 });
  return db;
}

function getDb() {
  if (!db) {
    throw new Error("Database is not connected yet.");
  }
  return db;
}

module.exports = {
  connectToDatabase,
  getDb
};
