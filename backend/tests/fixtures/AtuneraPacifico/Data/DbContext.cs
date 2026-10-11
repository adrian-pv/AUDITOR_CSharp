using System.Data.SqlClient;
using System.Security.Cryptography;
using System.Runtime.Serialization.Formatters.Binary;

namespace AtuneraPacifico.Data
{
    public class DbContext
    {
        public void Conectar(string cadena)
        {
            var connection = new SqlConnection(cadena);
            connection.Open();
        }

        public byte[] Hash(byte[] datos)
        {
            var md5 = MD5.Create();
            return md5.ComputeHash(datos);
        }

        public object Cargar(Stream flujo)
        {
            var formatter = new BinaryFormatter();
            return formatter.Deserialize(flujo);
        }

        public int Token()
        {
            var aleatorio = new Random();
            return aleatorio.Next();
        }
    }
}
