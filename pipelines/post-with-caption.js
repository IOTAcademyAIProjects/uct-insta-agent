#!/usr/bin/env node
/**
 * Instagram Post Pipeline with AI-Generated Captions
 * Usage: node post-with-caption.js IMAGE_URL DESCRIPTION TONE
 */

const path = require('path');
const axios = require('axios');
const FormData = require('form-data');
const https = require('https');
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

const { Composio } = require('composio-core');
const { Anthropic } = require('@anthropic-ai/sdk');

async function generateCaption(imageDescription, tone = 'casual') {
  try {
    const client = new Anthropic({
      apiKey: process.env.ANTHROPIC_API_KEY
    });

    const prompt = `Generate an Instagram caption for an image.

Image Description: ${imageDescription}
Tone: ${tone}

Requirements:
- 1-3 sentences, engaging and authentic
- Include 3-5 relevant hashtags
- Keep it conversational but aligned with the ${tone} tone
- Don't use emojis unless they naturally fit the tone

Return ONLY the caption text with hashtags, nothing else.`;

    const message = await client.messages.create({
      model: 'claude-opus-4-7',
      max_tokens: 150,
      messages: [
        { role: 'user', content: prompt }
      ]
    });

    return message.content[0].type === 'text' ? message.content[0].text.trim() : '';
  } catch (error) {
    console.error('Caption generation error:', error.message);
    return `Check out this ${tone.toLowerCase()} moment! 📸 #photography`;
  }
}

async function uploadToImgbb(imageUrl) {
  try {
    const apiKey = process.env.IMGBB_API_KEY;
    if (!apiKey) {
      throw new Error('IMGBB_API_KEY not set in environment');
    }

    // Download image
    const response = await axios.get(imageUrl, {
      responseType: 'arraybuffer'
    });
    const imageBuffer = Buffer.from(response.data);

    // Upload to imgbb using URLSearchParams and buffer
    const form = new FormData();
    form.append('image', imageBuffer, 'image.jpg');

    const uploadResponse = await axios.post(
      'https://api.imgbb.com/1/upload',
      form,
      {
        params: { key: apiKey },
        headers: form.getHeaders(),
        maxBodyLength: Infinity,
        maxContentLength: Infinity
      }
    );

    if (uploadResponse.data.success) {
      return uploadResponse.data.data.url;
    } else {
      throw new Error(`imgbb upload failed: ${JSON.stringify(uploadResponse.data)}`);
    }
  } catch (error) {
    if (error.response) {
      throw new Error(`Failed to upload to imgbb: ${error.response.status} ${JSON.stringify(error.response.data)}`);
    }
    throw new Error(`Failed to upload to imgbb: ${error.message}`);
  }
}

async function postToInstagram(imageUrl, caption) {
  try {
    const apiKey = process.env.COMPOSIO_API_KEY;
    if (!apiKey) {
      throw new Error('COMPOSIO_API_KEY not set in environment');
    }

    // Upload image to imgbb first
    console.error('Uploading image to imgbb...');
    const directImageUrl = await uploadToImgbb(imageUrl);
    console.error(`Image uploaded: ${directImageUrl}`);

    const client = new Composio({ apiKey });

    // Get connected account info
    const accounts = await client.connectedAccounts.list();
    if (!accounts.items || accounts.items.length === 0) {
      throw new Error('No Instagram account connected in Composio');
    }

    const userId = accounts.items[0].user_id;
    const connectedAccountId = accounts.items[0].id;
    const igUserId = process.env.INSTAGRAM_USER_ID;

    if (!igUserId) {
      throw new Error('INSTAGRAM_USER_ID not set in environment');
    }

    // Step 1: Create media container
    const step1 = await client.tools.execute(
      {
        slug: 'INSTAGRAM_CREATE_MEDIA_CONTAINER',
        arguments: {
          image_url: directImageUrl,
          caption: caption,
          media_type: 'IMAGE',
          ig_user_id: igUserId
        },
        connected_account_id: connectedAccountId,
        user_id: userId
      }
    );

    if (!step1.successful) {
      throw new Error(`Failed to create container: ${step1.error || 'Unknown error'}`);
    }

    const creationId = step1.data.id;

    // Step 2: Publish
    const step2 = await client.tools.execute(
      {
        slug: 'INSTAGRAM_CREATE_POST',
        arguments: {
          ig_user_id: igUserId,
          creation_id: creationId
        },
        connected_account_id: connectedAccountId,
        user_id: userId
      }
    );

    if (!step2.successful) {
      throw new Error(`Failed to publish: ${step2.error || 'Unknown error'}`);
    }

    return step2.data.id;
  } catch (error) {
    throw error;
  }
}

async function main() {
  if (process.argv.length < 3) {
    console.error('Usage: node post-with-caption.js IMAGE_URL [DESCRIPTION] [TONE]');
    process.exit(1);
  }

  const imageUrl = process.argv[2];
  const description = process.argv[3] || 'a beautiful image';
  let tone = process.argv[4] || 'casual';

  try {
    // Validate tone
    const validTones = ['casual', 'inspirational', 'professional', 'funny'];
    if (!validTones.includes(tone)) {
      tone = 'casual';
    }

    // Generate caption
    console.error(`Generating ${tone} caption for: ${description}`);
    const caption = await generateCaption(description, tone);
    console.error(`Generated caption: ${caption}`);

    // Post to Instagram
    console.error('Posting to Instagram...');
    const postId = await postToInstagram(imageUrl, caption);

    // Print success
    console.log('SUCCESS');
    console.log(`Post ID: ${postId}`);
    console.log('URL: https://instagram.com/iot_academy_projects');
  } catch (error) {
    console.error(`ERROR: ${error.message}`);
    console.log(`FAILED: ${error.message}`);
    process.exit(1);
  }
}

main();
