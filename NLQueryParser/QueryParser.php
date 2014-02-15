<?php
namespace NLQueryParser;

class QueryParser 
{
    const DEFAULT_BASE_URL = "localhost:5000/queryparser";

    /**
     * make a call to python code that will parse the query
     * @return JSON encoded string response from python
     */
    public static function parse($query_text, $user, $auth, $base_url=""){
        // test if args are not complete
        if ( empty($query_text) ){
            trigger_error("query is empty");
        }
        if ( empty($user) ){
            trigger_error("user is empty");
        }
        if ( empty($auth) ){
            trigger_error("auth string is empty");
        }
        if ( empty($base_url) ){
            $base_url = self::DEFAULT_BASE_URL;
        }

        // build url for API call
        $data = array("text"=>$query_text, "user"=>$user, "auth"=>$auth);
        $url = sprintf("%s?%s", $base_url, http_build_query($data) );

        // build + send curl request
        $curl = curl_init();
        curl_setopt($curl, CURLOPT_URL, $url);
        curl_setopt($curl, CURLOPT_RETURNTRANSFER, 1);

        $response = curl_exec($curl);

        curl_close($curl);

        return $response;
    }
}

?>
