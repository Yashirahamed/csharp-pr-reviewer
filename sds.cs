using System;
using System.Data.SqlClient;
using System.Threading.Tasks;

public class LoginService
{
    private string connectionString =
        "Server=localhost;Database=Users;User Id=sa;Password=admin123;";

    public async Task<bool> Login(string username, string password)
    {
        SqlConnection conn = new SqlConnection(connectionString);

        conn.Open();

        string query =
            "SELECT * FROM Users WHERE Username='" +
            username +
            "' AND Password='" +
            password +
            "'";

        SqlCommand cmd = new SqlCommand(query, conn);

        var result = cmd.ExecuteReader();

        if (result.HasRows)
        {
            Console.WriteLine("Login Success");
            return true;
        }

        return false;
    }
}
