const { execSync } = require('child_process');

module.exports = {
  name: 'instagram-post-image',
  description: 'Post a single image to Instagram. Use when user sends an image and wants to post it to Instagram with a caption.',

  async run({ imageUrl, caption }) {
    const script = [
      'import os, sys',
      'from dotenv import load_dotenv',
      'load_dotenv()',
      'from composio import Composio',
      'client = Composio(api_key=os.getenv("COMPOSIO_API_KEY"))',
      'accounts = client.connected_accounts.list()',
      'items = dict(accounts)["items"]',
      'user_id = items[0].user_id',
      'connected_account_id = items[0].id',
      'ig_user_id = os.getenv("INSTAGRAM_USER_ID")',
      `step1 = client.tools.execute(slug="INSTAGRAM_CREATE_MEDIA_CONTAINER", arguments={"image_url": "${imageUrl}", "caption": "${caption}", "media_type": "IMAGE", "ig_user_id": ig_user_id}, connected_account_id=connected_account_id, user_id=user_id, dangerously_skip_version_check=True)`,
      'if not step1["successful"]: print("ERROR:" + str(step1["error"])); sys.exit(1)',
      'creation_id = step1["data"]["id"]',
      `step2 = client.tools.execute(slug="INSTAGRAM_CREATE_POST", arguments={"ig_user_id": ig_user_id, "creation_id": creation_id}, connected_account_id=connected_account_id, user_id=user_id, dangerously_skip_version_check=True)`,
      'print("SUCCESS:" + step2["data"]["id"]) if step2["successful"] else print("ERROR:" + str(step2["error"]))'
    ].join('\n');

    try {
      const result = execSync(`python3 -c '${script}'`).toString().trim();
      if (result.startsWith('SUCCESS:')) {
        const postId = result.replace('SUCCESS:', '');
        return `Posted to Instagram successfully! Post ID: ${postId}`;
      } else {
        return `Failed to post: ${result.replace('ERROR:', '')}`;
      }
    } catch (error) {
      return `Error: ${error.message}`;
    }
  }
};
