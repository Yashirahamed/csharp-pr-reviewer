public class Demo
{
    private string password = "admin123";

    public void Login(string user)
    {
        string query = "SELECT * FROM Users WHERE Name='" + user + "'";
    }
}