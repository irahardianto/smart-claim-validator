import axios from 'axios';

const API_URL = '/api'; // Proxied to localhost:8383 via Vite

export const validateClaim = async (imageBase64, claimType) => {
  const payload = {
    appName: "claim_validator",
    newMessage: {
      role: "user",
      parts: [
        {
          text: `Check this ${claimType} claim.`,
          inlineData: {
            mimeType: "image/png", // Assuming PNG for simplicity, should detect
            data: imageBase64.split(',')[1] // Remove header
          }
        }
      ]
    }
  };

  try {
    const response = await axios.post(`${API_URL}/run`, payload);
    return response.data;
  } catch (error) {
    console.error("API Error:", error);
    throw error;
  }
};
