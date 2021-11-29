"""Tests for /envelope routes."""

from unittest import main, IsolatedAsyncioTestCase as TestCase
from uuid import UUID

from db_wrapper.model import sql

# internal test dependencies
from tests.helpers.application import (
    get_test_client,
    get_token_header,
)
from tests.helpers.database import (
    setup_user,
    # setup_account,
    # setup_transactions,
)

BASE_URL = "/envelope"


class TestRoutePostRoot(TestCase):
    """Testing POST /envelope."""

    async def test_valid_request(self) -> None:
        """Testing a valid request's response."""
        async with get_test_client() as clients:
            client, database = clients

            user_id = await setup_user(database)

            new_envelope = {
                "name": "envelope",
            }

            response = await client.post(
                BASE_URL,
                headers={
                    **get_token_header(user_id),
                    "accept": "application/json"},
                json=new_envelope)

            with self.subTest(
                    msg="Responds with a status code of 201."):
                self.assertEqual(201, response.status_code)

            with self.subTest(
                    msg="Responds with newly created Envelope's data."):
                body = response.json()

                with self.subTest(msg="Saves the given name."):
                    self.assertEqual(body["name"], new_envelope["name"])
                with self.subTest(msg="Bound to current user in auth token."):
                    self.assertEqual(body["user_id"], str(user_id))
                with self.subTest(msg="Has a UUID identifier."):
                    self.assertTrue(UUID(body["id"]))
                with self.subTest(msg="Starts with zero funds."):
                    self.assertEqual(body["total_funds"], 0)

            with self.subTest(msg="Saves the Envelope to the database."):
                body = response.json()
                new_id = UUID(body["id"])

                await database.connect()
                query_result = await database.execute_and_return(sql.SQL("""
                    SELECT * FROM envelope
                    WHERE id = {new_id};
                """).format(new_id=sql.Literal(new_id)))
                await database.disconnect()

                result = query_result[0]

                with self.subTest(
                    msg="Given envelope name & database envelope name match."
                ):
                    self.assertEqual(result["name"], new_envelope["name"])
                with self.subTest(msg="Binds to currently auth'd user."):
                    self.assertEqual(result["user_id"], user_id)
                with self.subTest(msg="Starts with 0 funds."):
                    self.assertEqual(result["total_funds"], 0)


class TestRouteGetRoot(TestCase):
    """Testing GET /envelope."""

    async def test_valid_request(self) -> None:
        """Testing a valid request's response."""
        async with get_test_client() as clients:
            client, database = clients

            user_id = await setup_user(database, "first")
            other_id = await setup_user(database, "other")

            add_envelope_query = sql.SQL("""
                INSERT INTO envelope
                    (name, total_funds, user_id)
                VALUES
                    ('envelope', 1.00, {user_id}),
                    ('envelope', 1.00, {user_id}),
                    ('envelope', 1.00, {user_id}),
                    ('envelope', 1.00, {other_id});
            """).format(
                user_id=sql.Literal(user_id),
                other_id=sql.Literal(other_id))

            await database.connect()
            await database.execute(add_envelope_query)
            await database.disconnect()

            response = await client.get(
                BASE_URL,
                headers={
                    **get_token_header(user_id),
                    "accept": "application/json"})

            with self.subTest(
                    msg="Responds with a status code of 200."):
                self.assertEqual(200, response.status_code)

            with self.subTest(
                msg="Responds w/ all Envelopes belonging to current user."
            ):
                body = response.json()

                self.assertEqual(
                    len(body), 3, msg="Body should contain 3 Envelopes.")

                for item in body:
                    with self.subTest(msg="Envelope has a name."):
                        self.assertEqual(item["name"], "envelope")
                    with self.subTest(
                            msg="Bound to current user in auth token."):
                        self.assertEqual(item["user_id"], str(user_id))
                    with self.subTest(msg="Envelope has a UUID identifier."):
                        self.assertTrue(UUID(item["id"]))
                    with self.subTest(msg="Envelope has funds."):
                        self.assertEqual(item["total_funds"], 1.00)


class TestRouteGetId(TestCase):
    """Testing GET /envelope/{id}."""

    async def test_valid_request(self) -> None:
        """Testing a valid request's response."""
        async with get_test_client() as clients:
            client, database = clients

            user_id = await setup_user(database, "first")

            add_envelope_query = sql.SQL("""
                INSERT INTO envelope
                    (name, total_funds, user_id)
                VALUES
                    ('envelope', 1.00, {user_id})
                RETURNING
                    id;
            """).format(
                user_id=sql.Literal(user_id))

            await database.connect()
            query_result = \
                await database.execute_and_return(add_envelope_query)
            await database.disconnect()
            envelope_id = query_result[0]["id"]

            response = await client.get(
                f"{BASE_URL}/{envelope_id}",
                headers={
                    **get_token_header(user_id),
                    "accept": "application/json"})

            with self.subTest(
                    msg="Responds with a status code of 200."):
                self.assertEqual(200, response.status_code)

            with self.subTest(
                    msg="Responds with requested Envelope's data."):
                body = response.json()

                with self.subTest(msg="Includes the Envelope's name."):
                    self.assertEqual(body["name"], "envelope")
                with self.subTest(msg="Bound to current user in auth token."):
                    self.assertEqual(body["user_id"], str(user_id))
                with self.subTest(msg="Has a UUID identifier."):
                    self.assertEqual(body["id"], str(envelope_id))
                with self.subTest(msg="Includes Envelope's funds."):
                    self.assertEqual(body["total_funds"], 1)

    async def test_can_only_get_own_envelopes(self) -> None:
        """A User can't get another User's Envelopes."""
        async with get_test_client() as clients:
            client, database = clients

            user_id = await setup_user(database, "first")
            other_id = await setup_user(database, "other")

            add_envelope_query = sql.SQL("""
                INSERT INTO envelope
                    (name, total_funds, user_id)
                VALUES
                    ('envelope', 1.00, {user_id})
                RETURNING
                    id;
            """).format(
                user_id=sql.Literal(user_id))

            await database.connect()
            query_result = \
                await database.execute_and_return(add_envelope_query)
            await database.disconnect()
            envelope_id = query_result[0]["id"]

            response = await client.get(
                f"{BASE_URL}/{envelope_id}",
                headers={
                    **get_token_header(other_id),
                    "accept": "application/json"})

            with self.subTest(
                    msg="Responds with a status code of 404."):
                self.assertEqual(404, response.status_code)


if __name__ == "__main__":
    main()
