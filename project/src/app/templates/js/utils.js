//// get token
////async function callApi(token: String) {
//

async function callApi() {
    try {
        let token = ""
        let apiUrl = 'http://localhost:8000/verify_token'

        // Query parameters
        const queryParams = {
            token: token,
        };

        // Constructing the URL with query parameters
        const urlWithParams = new URL(apiUrl);
        Object.keys(queryParams).forEach(key => urlWithParams.searchParams.append(key, queryParams[key]));

        const response = await fetch(urlWithParams);

        console.log("token: ")
        console.log(token)

        console.log("response: ")
        console.log(response)

        if (response.ok) {
            // Token is correct, navigate to the desired page
            window.location.href = 'http://localhost:8000/transcribe';
        } else {
            // Token is invalid
            alert('Invalid token');
        }
    } catch (error) {
        console.error('Error calling API:', error);
    }
}

