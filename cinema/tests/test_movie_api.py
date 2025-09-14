import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor, Order, Ticket
from cinema.serializers import TicketSerializer
from user.models import User

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")
GENRE_URL = reverse("cinema:genre-list")
ORDERS_URL = reverse("cinema:order-list")


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_genre(**params):
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


def sample_movie_session(**params):
    cinema_hall = CinemaHall.objects.create(name="Blue", rows=20, seats_in_row=20)

    defaults = {
        "show_time": "2022-06-02 14:00:00",
        "movie": None,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)

    return MovieSession.objects.create(**defaults)


def image_upload_url(movie_id):
    """Return URL for recipe image upload"""
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class MovieImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_session = sample_movie_session(movie=self.movie)

    def tearDown(self):
        self.movie.image.delete()

    def test_upload_image_to_movie(self):
        """Test uploading an image to movie"""
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.movie.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.movie.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_movie_list(self):
        url = MOVIE_URL
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                {
                    "title": "Title",
                    "description": "Description",
                    "duration": 90,
                    "genres": [1],
                    "actors": [1],
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="Title")
        self.assertFalse(movie.image)

    def test_image_url_is_shown_on_movie_detail(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(self.movie.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_movie_list(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_URL)

        self.assertIn("image", res.data[0].keys())

    def test_image_url_is_shown_on_movie_session_detail(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_SESSION_URL)

        self.assertIn("movie_image", res.data[0].keys())


class GenreListTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)

    def test_genre_list_returns_list_of_genres(self):
        Genre.objects.create(name="aboba")
        Genre.objects.create(name="pupalupa")

        res = self.client.get(GENRE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)


class MovieFilterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.genre1 = sample_genre(name="drama")
        self.genre2 = sample_genre(name="comedy")
        self.actor1 = sample_actor(first_name="Clint", last_name="Eastwood")
        self.actor2 = sample_actor(first_name="Uma", last_name="Thurman")

        self.movie1 = sample_movie()
        self.movie1.genres.add(self.genre1)
        self.movie1.actors.add(self.actor1)

        self.movie2 = Movie.objects.create(
            title="funny movie",
            description="A very funny film",
            duration=90
        )
        self.movie2.genres.add(self.genre2)
        self.movie2.actors.add(self.actor2)

        self.movie3 = Movie.objects.create(
            title="mixed movie",
            description="has both genres",
            duration=110
        )
        self.movie3.genres.set([self.genre1.id, self.genre2.id])
        self.movie3.actors.set([self.actor1.id, self.actor2.id])

    def test_filter_by_title(self):
        res = self.client.get(MOVIE_URL, {"title": "funny"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        returned_titles = [m["title"] for m in res.data]
        self.assertIn(self.movie2.title, returned_titles)
        self.assertNotIn(self.movie1.title, returned_titles)

    def test_filter_by_genres(self):
        res = self.client.get(MOVIE_URL, {"genres": f"{self.genre1.id}"})
        returned_ids = [movie["id"] for movie in res.data]
        self.assertIn(self.movie1.id, returned_ids)
        self.assertIn(self.movie3.id, returned_ids)
        self.assertNotIn(self.movie2.id, returned_ids)

    def test_filter_by_actors(self):
        res = self.client.get(MOVIE_URL, {"actors": f"{self.actor1.id}"})
        returned_ids = [actor["id"] for actor in res.data]
        self.assertIn(self.movie1.id, returned_ids)
        self.assertIn(self.movie3.id, returned_ids)
        self.assertNotIn(self.movie2.id, returned_ids)


class OrderViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.user_client = User.objects.create_user(
            email="user2@test.com", password="pass123"
        )

        self.movie = sample_movie()
        self.movie_session = sample_movie_session(movie=self.movie)

        self.order1 = Order.objects.create(user=self.user_client)
        Ticket.objects.create(
            order=self.order1, movie_session=self.movie_session, row=1, seat=5
        )

        self.order2 = Order.objects.create(user=self.admin)
        Ticket.objects.create(
            order=self.order2, movie_session=self.movie_session, row=5, seat=15
        )

    def test_user_sees_only_own_orders(self):
        self.client.force_authenticate(self.user_client)
        res = self.client.get(ORDERS_URL)
        print(Order.objects.all())

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 4)
        self.assertEqual(res.data["results"][0]["id"], self.order1.id)


class TicketValidationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.movie_session = sample_movie_session(movie=self.movie)

    def test_ticket_created(self):
        data = {
            "row": 5,
            "seat": 10,
            "movie_session": self.movie_session.id,
        }
        serializer = TicketSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_seat_raises_error(self):
        data = {
            "row": 5,
            "seat": 25,
            "movie_session": self.movie_session.id,
        }
        serializer = TicketSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        error_text = str(serializer.errors)
        self.assertIn("seat number must be in available range", error_text)
