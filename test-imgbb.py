import os
import requests
from dotenv import load_dotenv
load_dotenv()

# Test 1 - Upload image to imgbb
print('Testing imgbb upload...')

image_url = 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1080'

# Download image first
img_data = requests.get(image_url).content

# Upload to imgbb
response = requests.post(
    'https://api.imgbb.com/1/upload',
    params={'key': os.getenv('IMGBB_API_KEY')},
    files={'image': img_data}
)

result = response.json()
print('imgbb response:', result)

if result['success']:
    direct_url = result['data']['url']
    print('Direct image URL:', direct_url)
    
    # Test 2 - Post to Instagram
    print('\nPosting to Instagram...')
    from composio import Composio
    
    client = Composio(api_key=os.getenv('COMPOSIO_API_KEY'))
    accounts = client.connected_accounts.list()
    items = dict(accounts)['items']
    user_id = items[0].user_id
    connected_account_id = items[0].id
    ig_user_id = os.getenv('INSTAGRAM_USER_ID')
    
    step1 = client.tools.execute(
        slug='INSTAGRAM_CREATE_MEDIA_CONTAINER',
        arguments={
            'image_url': direct_url,
            'caption': 'Posted via uct-insta-agent! 🤖 #AI #automation',
            'media_type': 'IMAGE',
            'ig_user_id': ig_user_id
        },
        connected_account_id=connected_account_id,
        user_id=user_id,
        dangerously_skip_version_check=True
    )
    print('Step 1:', step1)
    
    if step1['successful']:
        creation_id = step1['data']['id']
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
        print('Step 2:', step2)
        if step2['successful']:
            print('\nSUCCESS! Full flow working!')
            print('Post ID:', step2['data']['id'])
        else:
            print('Step 2 failed:', step2['error'])
    else:
        print('Step 1 failed:', step1['error'])
else:
    print('imgbb upload failed:', result)
