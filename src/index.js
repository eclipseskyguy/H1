import 'dotenv/config';

async function authenticate() {
    const url = "https://m2m.cr.usgs.gov/api/api/json/stable/login-token";

    const payload = {
        "username": process.env.USGS_USERNAME,
        "token": process.env.USGS_API_TOKEN
    }

    try {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`Request failed with status ${response.status}: ${text}`);
        }

        const data = JSON.parse(await response.text());
        console.log(data)
        return data.data;
    } catch (error) {
        console.error("Authentication Error:", error);
        return null;
    }
}

authenticate();
