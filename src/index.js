import 'dotenv/config';
import fs from 'fs';

async function authenticate() {
    const url = "https://m2m.cr.usgs.gov/api/api/json/stable/login-token";

    const payload = {
        "username": process.env.USGS_USERNAME,
        "token": process.env.USGS_API_TOKEN
    };

    try {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`Request failed with status ${response.status}`);
        }

        const data = await response.json();
        console.log("Auth Response:", data);

        if (data.errorCode) {
            throw new Error(`Auth Failed: ${data.errorMessage}`);
        }

        return data.data; // This is the API Key
    } catch (error) {
        console.error("Authentication Error:", error);
        return null;
    }
}

authenticate().then(apiKey => {
    searchDatasets(apiKey)
});

async function searchDatasets(apiKey) {
    const url = "https://m2m.cr.usgs.gov/api/api/json/stable/dataset-search";
    const payload = { datasetName: "Landsat" };

    const response = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Auth-Token": apiKey
        },
        body: JSON.stringify(payload)
    });

    const data = await response.json();
    fs.writeFileSync("datasets.json", JSON.stringify(data.data, null, 2));
    console.log("Available Datasets:", data);
}
