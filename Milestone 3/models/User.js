const { getDb } = require("../db");

const USERS_COLLECTION = "users";

function usersCollection() {
  return getDb().collection(USERS_COLLECTION);
}

async function ensureUserIndexes() {
  await usersCollection().createIndex({ email: 1 }, { unique: true });
}

async function findUserByEmail(email) {
  return usersCollection().findOne({ email });
}

async function createUser(user) {
  await usersCollection().insertOne(user);
  return user;
}

module.exports = {
  ensureUserIndexes,
  findUserByEmail,
  createUser
};
