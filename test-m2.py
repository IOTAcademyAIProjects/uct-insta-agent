import os
from dotenv import load_dotenv
load_dotenv()
from composio import Composio

client = Composio(api_key=os.getenv('COMPOSIO_API_KEY'))
accounts = client.connected_accounts.list()
items = dict(accounts)['items']
user_id = items[0].user_id
connected_account_id = items[0].id
ig_user_id = os.getenv('INSTAGRAM_USER_ID')

print('Account:', connected_account_id)
print('IG User ID:', ig_user_id)

# Test image and caption
image_url = 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1080'
caption = 'Hello from uct-insta-agent! Built with OpenClaw + Claude + Composio #AI #automation #python'

print('Posting image...')

# Step 1 - Create container
step1 = client.tools.execute(
    slug='INSTAGRAM_CREATE_MEDIA_CONTAINER',
    arguments={
        'image_url': image_url,
        'caption': caption,
        'media_type': 'IMAGE',
        'ig_user_id': ig_user_id
    },
    connected_account_id=connected_account_id,
    user_id=user_id,
    dangerously_skip_version_check=True
)
print('Step 1 - Container created:', step1)

if not step1['successful']:
    print('FAILED at step 1:', step1['error'])
    exit(1)

creation_id = step1['data']['id']
print('Creation ID:', creation_id)

# Step 2 - Publish
step2 = client.tools.execute(
    slug='INSTAGRAM_CREATE_POST',
    arguments={
        'ig_user_id': ig_user_id,
        'creation_id': creation_id
    },
    connected_account_id=connected_account_id,
    user_id=user_id,
    dangerously_skip_version_check=True
)
print('Step 2 - Published:', step2)

if step2['successful']:
    post_id = step2['data']['id']
    print('')
    print('SUCCESS! Post published!')
    print('Post ID:', post_id)
    print('Check Instagram: https://instagram.com/iot_academy_projects')
else:
    print('FAILED at step 2:', step2['error'])
