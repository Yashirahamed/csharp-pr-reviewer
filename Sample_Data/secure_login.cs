public class LoginService
{
    public void Login(string user)
    {
        if (string.IsNullOrWhiteSpace(user))
            throw new ArgumentException("Invalid username");

        string query =
            "SELECT * FROM Users WHERE Name=@username";
    }
}