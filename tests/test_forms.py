# -*- coding: utf-8 -*-
"""Test forms."""

from dribdat.public.forms import LoginForm
from dribdat.user.forms import RegisterForm

import pytest

class TestRegisterForm:
    """Register form."""

    def test_validate_user_already_registered(self, user):
        """Enter username that is already registered."""
        form = RegisterForm(username=user.username, email='foo@bar.com',
                            password='example', confirm='example')

        assert form.validate() is False
        assert 'A user with this name already exists' in form.username.errors


    def test_validate_email_already_registered(self, user):
        """Enter email that is already registered."""
        form = RegisterForm(username='unique', email=user.email,
                            password='example', confirm='example')

        assert form.validate() is False
        assert 'Email already registered' in form.email.errors


    def test_validate_success(self, db):
        """Register with success."""
        form = RegisterForm(username='newusername', email='new@test.test',
                            password='example', confirm='example')
        assert form.validate() is True


class TestLoginForm:
    """Login form."""


    def test_validate_success(self, user):
        """Login successful."""
        user.set_password('example')
        user.save()
        form = LoginForm(username=user.username, password='example')
        assert form.validate() is True
        assert form.user == user


    def test_validate_unknown_username(self, db):
        """Unknown username."""
        form = LoginForm(username='unknown', password='example')
        assert form.validate() is False
        assert 'Unknown username' in form.username.errors
        assert form.user is None


    def test_validate_invalid_password(self, user):
        """Invalid password."""
        user.set_password('example')
        user.save()
        form = LoginForm(username=user.username, password='wrongpassword')
        assert form.validate() is False
        assert 'Invalid password' in form.password.errors


    def test_validate_inactive_user(self, user, testapp):
        """Inactive user."""
        user.active = False
        user.set_password('example')
        user.save()
        # Correct username and password, but user is not activated
        form = LoginForm(username=user.username, password='example')
        # Deactivated use can still log in
        assert form.validate() is True
        res = testapp.get('/user/%s' % user.username)
        assert 'under review' in res
