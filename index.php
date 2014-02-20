<!DOCTYPE html>
<html>
<h1>Query Parser Test Page</h1>
<body>
    <div id="query-ui">
    <form action="" method="get">
        <input type="text" name="query" style="width: 300px">
        <input type="submit" value="Go">
    </form>
    <?php
        function __autoload($className)
        {
            $className = ltrim($className, '\\');
            $fileName  = '';
            $namespace = '';
            if ($lastNsPos = strrpos($className, '\\')) {
                $namespace = substr($className, 0, $lastNsPos);
                $className = substr($className, $lastNsPos + 1);
                $fileName  = str_replace('\\', DIRECTORY_SEPARATOR, $namespace) . DIRECTORY_SEPARATOR;
            }
            $fileName .= str_replace('_', DIRECTORY_SEPARATOR, $className) . '.php';

            require $fileName;
        }
        $query_text = stripslashes($_GET['query']);
        $networks = array('NBC', 'MSNBC', 'NBCUniversal');
        if ( isset( $query_text) ){
            $res = \NLQueryParser\QueryParser::parse($query_text, 
               "test_auth", $networks, "localhost:5000/parse");
            echo "<h3>QUERY:</h3><p>".$query_text."</p>";
            echo "<h3>RESULT:</h3><p>".$res."</p>";
        }
    ?>

</body>
</html>
