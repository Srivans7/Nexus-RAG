"""Google OAuth2 authentication views and JWT token management."""

import json
import logging
from datetime import datetime, timedelta

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
import jwt
from django.conf import settings
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import UserProfile

logger = logging.getLogger(__name__)

JWT_SECRET = getattr(settings, 'JWT_SECRET_KEY', 'default-secret-key-change-in-production')
JWT_EXPIRY_HOURS = getattr(settings, 'JWT_EXPIRY_HOURS', 24)
GOOGLE_OAUTH_CLIENT_ID = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '')


def generate_jwt_token(user: User) -> str:
	"""Generate a JWT token for authenticated user."""
	payload = {
		'user_id': user.id,
		'email': user.email,
		'username': user.username,
		'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
		'iat': datetime.utcnow(),
	}
	return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


def verify_jwt_token(token: str) -> dict | None:
	"""Verify JWT token and return payload if valid."""
	try:
		payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
		return payload
	except jwt.ExpiredSignatureError:
		return None
	except jwt.InvalidTokenError:
		return None


@csrf_exempt
@api_view(['POST'])
def google_oauth_login(request):
	"""Handle Google OAuth2 login.

	Expected request body:
	{
		"credential": "..."
	}
	"""
	try:
		data = json.loads(request.body.decode('utf-8') or '{}')
	except json.JSONDecodeError:
		return Response({'detail': 'Invalid JSON payload.'}, status=status.HTTP_400_BAD_REQUEST)

	credential = data.get('credential')
	if not credential:
		return Response({'detail': 'Google credential is required.'}, status=status.HTTP_400_BAD_REQUEST)

	if not GOOGLE_OAUTH_CLIENT_ID:
		logger.error('GOOGLE_OAUTH_CLIENT_ID is not configured on the backend.')
		return Response({'detail': 'Google sign-in is not configured.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

	try:
		verified_token = google_id_token.verify_oauth2_token(
			credential,
			google_requests.Request(),
			GOOGLE_OAUTH_CLIENT_ID,
		)
	except ValueError:
		return Response({'detail': 'Invalid Google credential.'}, status=status.HTTP_400_BAD_REQUEST)

	google_id = verified_token.get('sub')
	email = verified_token.get('email')
	name = verified_token.get('name')
	picture = verified_token.get('picture')

	if not google_id or not email:
		return Response(
			{'detail': 'Verified Google profile is missing required fields.'},
			status=status.HTTP_400_BAD_REQUEST,
		)

	user, created = User.objects.get_or_create(
		email=email,
		defaults={'username': email.split('@')[0], 'first_name': name or ''},
	)

	profile, _ = UserProfile.objects.get_or_create(
		user=user,
		defaults={'google_id': google_id, 'avatar_url': picture or ''},
	)

	if not created:
		profile.google_id = google_id
		profile.avatar_url = picture or ''
		profile.save()

	token = generate_jwt_token(user)

	return Response(
		{
			'token': token,
			'user': {
				'id': user.id,
				'email': user.email,
				'name': user.first_name or user.username,
				'avatar_url': profile.avatar_url,
			},
		},
		status=status.HTTP_200_OK,
	)


@api_view(['GET'])
def get_current_user(request):
	"""Return current authenticated user profile."""
	auth_header = request.headers.get('Authorization', '')
	if not auth_header.startswith('Bearer '):
		return Response({'detail': 'Missing or invalid authorization header.'}, status=status.HTTP_401_UNAUTHORIZED)

	token = auth_header[7:]
	payload = verify_jwt_token(token)
	if not payload:
		return Response({'detail': 'Invalid or expired token.'}, status=status.HTTP_401_UNAUTHORIZED)

	try:
		user = User.objects.get(id=payload['user_id'])
		profile = UserProfile.objects.get(user=user)
		return Response(
			{
				'user': {
					'id': user.id,
					'email': user.email,
					'name': user.first_name or user.username,
					'avatar_url': profile.avatar_url,
				},
			},
			status=status.HTTP_200_OK,
		)
	except (User.DoesNotExist, UserProfile.DoesNotExist):
		return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def logout(request):
	"""Logout endpoint (token revocation on client side)."""
	return Response({'detail': 'Logged out successfully.'}, status=status.HTTP_200_OK)


@api_view(['PUT'])
def update_profile(request):
	"""Update user profile information."""
	auth_header = request.headers.get('Authorization', '')
	if not auth_header.startswith('Bearer '):
		return Response({'detail': 'Missing or invalid authorization header.'}, status=status.HTTP_401_UNAUTHORIZED)

	token = auth_header[7:]
	payload = verify_jwt_token(token)
	if not payload:
		return Response({'detail': 'Invalid or expired token.'}, status=status.HTTP_401_UNAUTHORIZED)

	try:
		user = User.objects.get(id=payload['user_id'])
		profile = UserProfile.objects.get(user=user)

		try:
			data = json.loads(request.body.decode('utf-8') or '{}')
		except json.JSONDecodeError:
			return Response({'detail': 'Invalid JSON payload.'}, status=status.HTTP_400_BAD_REQUEST)

		if 'name' in data and data['name']:
			user.first_name = data['name']
			user.save()

		profile.avatar_url = data.get('avatar_url', profile.avatar_url)
		profile.save()

		return Response(
			{
				'user': {
					'id': user.id,
					'email': user.email,
					'name': user.first_name or user.username,
					'avatar_url': profile.avatar_url,
				},
			},
			status=status.HTTP_200_OK,
		)
	except (User.DoesNotExist, UserProfile.DoesNotExist):
		return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
