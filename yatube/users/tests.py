from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from http import HTTPStatus

User = get_user_model()


class TestUserUrls(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.client = Client()

        cls.user = User.objects.create_user(username='Kirill',
                                            password='Qzwxec1357',
                                            email='kirill@yandex.ru')

    def test_public_urls(self):
        public_urls = {
            '/auth/signup/': 'users/signup.html',
            '/auth/login/': 'users/login.html',
            '/auth/password_reset/': 'users/password_reset_form.html',
            '/auth/password_reset/done/': 'users/password_reset_done.html',
            '/auth/reset/done/': 'users/password_reset_complete.html'
        }
        for url, template in public_urls.items():
            with self.subTest(url=url):
                response = TestUserUrls.client.get(url)

                self.assertEqual(response.status_code,
                                 HTTPStatus.OK,
                                 f'Переход на страницу {url} '
                                 'работает некорректно, '
                                 'проверьте view-функцию.'
                                 )
                self.assertTemplateUsed(response,
                                        template,
                                        f'Для url {url} используется '
                                        'некорректный шаблон'
                                        )

        forms_data = {
            '/auth/signup/': (
                {
                    'firts_name': 'auth',
                    'last_name': 'user',
                    'username': 'auth_user',
                    'email': 'auth@user.com',
                    'password1': 'QzwxecrV15243',
                    'password2': 'QzwxecrV15243'
                }, '/'),
            '/auth/login/': (
                {
                    'username': 'Kirill',
                    'password': 'Qzwxec1357'
                }, '/'),
            '/auth/password_reset/': (
                {
                    'email': 'kirill@yandex.ru'
                }, '/auth/password_reset/done/')
        }

        for url, data in forms_data.items():
            with self.subTest(url=url):
                response = TestUserUrls.client.post(url, data[0])
                self.assertRedirects(response,
                                     data[1],
                                     status_code=HTTPStatus.FOUND,
                                     target_status_code=HTTPStatus.OK,
                                     msg_prefix=('Перенаправление пользователя'
                                                 f' со страницы {url} '
                                                 'работает некорректно.')
                                     )

    def setUp(self) -> None:
        super().setUp()
        TestUserUrls.client.force_login(TestUserUrls.user)

    def test_auth_urls(self):
        auth_urls = {
            '/auth/password_change/': 'users/password_change_form.html',
            '/auth/logout/': 'users/logged_out.html',
            '/auth/password_change/done/': 'users/password_change_done.html',
        }

        for url, template in auth_urls.items():
            with self.subTest(url=url):
                response = TestUserUrls.client.get(url)
                try:
                    self.assertEqual(response.status_code,
                                     HTTPStatus.OK,
                                     f'Переход на страницу {url} '
                                     'работает некорректно, '
                                     'проверьте view-функцию.'
                                     )
                    self.assertTemplateUsed(response,
                                            template,
                                            f'Для url {url} используется '
                                            'некорректный шаблон'
                                            )
                except AssertionError:
                    self.assertEqual(response.status_code,
                                     HTTPStatus.FOUND,
                                     f'Перенаправление на страницу {url} '
                                     'работает некорректно, '
                                     'проверьте view-функцию.'
                                     )

    def test_change_password_redirect(self):
        response = TestUserUrls.client.post('/auth/password_change/', {
                                            'old_password': 'Qzwxec1357',
                                            'new_password1': 'LKJHGfdsa2234',
                                            'new_password2': 'LKJHGfdsa2234'
                                            }
                                            )
        self.assertRedirects(response,
                             '/auth/password_change/done/',
                             status_code=HTTPStatus.FOUND,
                             target_status_code=HTTPStatus.OK,
                             msg_prefix=('Перенаправление пользователя '
                                         'со страницы изменения пароля '
                                         'работает некорректно.')
                             )
