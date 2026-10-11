// RoslynBridge
//
// Recibe la ruta de una carpeta de solución .NET, parsea cada archivo .cs con
// la interfaz de programación Roslyn (Microsoft.CodeAnalysis.CSharp) y escribe
// a stdout un AST simplificado en JSON (esquema documentado en
// backend/engine/ast_bridge.py).
//
// El puente NO decide qué es una vulnerabilidad: solo extrae hechos del árbol
// de sintaxis (literales, llamadas, asignaciones, clases, bloques catch...).
// Las reglas —y sus patrones, que el Administrador puede editar— viven en la
// base de datos y se evalúan en el motor de Python.
//
// Uso:
//   dotnet run --project roslyn-bridge -- <ruta-a-la-solucion>

using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

if (args.Length == 0)
{
    Console.Error.WriteLine("Uso: RoslynBridge <ruta-a-la-solucion>");
    return 1;
}

var raiz = args[0];
var resultados = new List<object>();

foreach (var ruta in Directory.EnumerateFiles(raiz, "*.cs", SearchOption.AllDirectories).OrderBy(r => r))
{
    var texto = File.ReadAllText(ruta);
    var arbol = CSharpSyntaxTree.ParseText(texto);
    var nodo = arbol.GetCompilationUnitRoot();
    var ex = new Extractor(arbol);

    resultados.Add(new
    {
        file = Path.GetRelativePath(raiz, ruta).Replace('\\', '/'),
        kind = "csharp",
        loc = texto.Split('\n').Length,
        declarations = ex.Declaraciones(nodo),
        literals = ex.Literales(nodo),
        invocations = ex.Invocaciones(nodo),
        assignments = ex.Asignaciones(nodo),
        concatenations = ex.Concatenaciones(nodo),
        classes = ex.Clases(nodo),
        catches = ex.Catches(nodo),
        comparisons = ex.Comparaciones(nodo),
        disposables = ex.Disposables(nodo),
    });
}

Console.WriteLine(JsonSerializer.Serialize(resultados));
return 0;

sealed class Extractor
{
    private readonly SyntaxTree _arbol;
    public Extractor(SyntaxTree arbol) => _arbol = arbol;

    private int Linea(SyntaxNode n) => _arbol.GetLineSpan(n.Span).StartLinePosition.Line + 1;

    // ---------------------------------------------------------------- declaraciones
    public List<object> Declaraciones(CompilationUnitSyntax raiz)
    {
        var lista = new List<object>();

        foreach (var prop in raiz.DescendantNodes().OfType<PropertyDeclarationSyntax>())
            lista.Add(new
            {
                kind = "property",
                name = prop.Identifier.Text,
                type = prop.Type.ToString(),
                modifiers = prop.Modifiers.Select(m => m.Text).ToArray(),
                line = Linea(prop),
            });

        foreach (var field in raiz.DescendantNodes().OfType<FieldDeclarationSyntax>())
            foreach (var v in field.Declaration.Variables)
                lista.Add(new
                {
                    kind = "field",
                    name = v.Identifier.Text,
                    type = field.Declaration.Type.ToString(),
                    modifiers = field.Modifiers.Select(m => m.Text).ToArray(),
                    line = Linea(field),
                });

        // Variables locales: 'used' = el identificador vuelve a aparecer en su
        // bloque después de declararse (análisis sintáctico, sin modelo semántico).
        foreach (var local in raiz.DescendantNodes().OfType<LocalDeclarationStatementSyntax>())
        {
            var bloque = local.Parent;
            foreach (var v in local.Declaration.Variables)
            {
                var nombre = v.Identifier.Text;
                var usada = bloque?.DescendantNodes()
                    .OfType<IdentifierNameSyntax>()
                    .Any(id => id.Identifier.Text == nombre && id.SpanStart > v.Span.End) ?? true;
                lista.Add(new
                {
                    kind = "variable",
                    name = nombre,
                    type = ResolverTipo(local.Declaration, v),
                    modifiers = local.Modifiers.Select(m => m.Text).ToArray(),
                    line = Linea(local),
                    used = usada || local.UsingKeyword.IsKind(SyntaxKind.UsingKeyword),
                });
            }
        }
        return lista;
    }

    // ---------------------------------------------------------------- literales
    public List<object> Literales(CompilationUnitSyntax raiz)
    {
        var lista = new List<object>();
        foreach (var lit in raiz.DescendantNodes().OfType<LiteralExpressionSyntax>()
                     .Where(l => l.IsKind(SyntaxKind.StringLiteralExpression)))
        {
            lista.Add(new
            {
                kind = "string",
                value = lit.Token.ValueText,
                line = Linea(lit),
                assigned_to = DestinoDeAsignacion(lit),
            });
        }
        return lista;
    }

    // Nombre al que se asigna el literal: variable, campo, propiedad o
    // miembro (x.Password = "..."), o argumento con nombre (password: "...").
    private static string? DestinoDeAsignacion(LiteralExpressionSyntax lit)
    {
        var padre = lit.Parent;
        if (padre is EqualsValueClauseSyntax eq)
        {
            if (eq.Parent is VariableDeclaratorSyntax d) return d.Identifier.Text;
            if (eq.Parent is PropertyDeclarationSyntax p) return p.Identifier.Text;
        }
        if (padre is AssignmentExpressionSyntax asig && asig.Right == lit)
            return UltimoNombre(asig.Left);
        if (padre is ArgumentSyntax arg && arg.NameColon != null)
            return arg.NameColon.Name.Identifier.Text;
        return null;
    }

    // ---------------------------------------------------------------- llamadas y "new"
    public List<object> Invocaciones(CompilationUnitSyntax raiz)
    {
        var lista = new List<object>();

        foreach (var inv in raiz.DescendantNodes().OfType<InvocationExpressionSyntax>())
        {
            var objetivo = inv.Expression.ToString();
            lista.Add(new
            {
                kind = "call",
                name = UltimoNombre(inv.Expression),
                target = Compactar(objetivo),
                line = Linea(inv),
                args = inv.ArgumentList.Arguments.Select(DescribirArgumento).ToList(),
            });
        }

        foreach (var nuevo in raiz.DescendantNodes().OfType<BaseObjectCreationExpressionSyntax>())
        {
            var tipo = nuevo is ObjectCreationExpressionSyntax oc ? oc.Type.ToString() : TipoImplicito(nuevo);
            lista.Add(new
            {
                kind = "new",
                name = tipo.Split('.').Last(),
                target = tipo,
                line = Linea(nuevo),
                args = nuevo.ArgumentList?.Arguments.Select(DescribirArgumento).ToList() ?? new List<object>(),
            });
        }
        return lista;
    }

    private static string TipoImplicito(BaseObjectCreationExpressionSyntax nuevo)
    {
        // new() con tipo implícito: se toma el tipo declarado de la variable si existe.
        if (nuevo.Parent is EqualsValueClauseSyntax { Parent: VariableDeclaratorSyntax { Parent: VariableDeclarationSyntax decl } })
            return decl.Type.ToString();
        return "";
    }

    private object DescribirArgumento(ArgumentSyntax a)
    {
        var e = a.Expression;
        var esLiteral = e is LiteralExpressionSyntax;
        var partes = PartesLiterales(e, a);
        return new
        {
            text = Compactar(e.ToString()),
            name = a.NameColon?.Name.Identifier.Text,
            literal = esLiteral,
            value = e is LiteralExpressionSyntax l ? l.Token.ValueText : null,
            concatenated = EsConcatenacion(e) || VariableConcatenada(e, a),
            dynamic = !esLiteral && !EsConstante(e),
            literal_parts = partes,
        };
    }

    // ---------------------------------------------------------------- asignaciones
    public List<object> Asignaciones(CompilationUnitSyntax raiz)
    {
        var lista = new List<object>();
        foreach (var asig in raiz.DescendantNodes().OfType<AssignmentExpressionSyntax>()
                     .Where(a => a.IsKind(SyntaxKind.SimpleAssignmentExpression)))
        {
            lista.Add(new
            {
                target = Compactar(asig.Left.ToString()),
                member = UltimoNombre(asig.Left),
                value = Compactar(asig.Right.ToString()),
                line = Linea(asig),
                concatenated = EsConcatenacion(asig.Right),
                literal_parts = PartesLiterales(asig.Right, asig),
            });
        }
        return lista;
    }

    // ---------------------------------------------------------------- concatenaciones
    // Cadenas construidas con '+' o interpolación ($"...{x}") que mezclan texto
    // fijo con valores dinámicos. Solo la expresión más externa de cada cadena.
    public List<object> Concatenaciones(CompilationUnitSyntax raiz)
    {
        var lista = new List<object>();
        foreach (var e in raiz.DescendantNodes().OfType<ExpressionSyntax>().Where(EsConcatenacion))
        {
            if (e.Parent is ExpressionSyntax p && EsConcatenacion(p)) continue;
            if (e.Parent is ParenthesizedExpressionSyntax) continue;
            var partes = new List<string>();
            var dinamica = false;
            Recorrer(e, partes, ref dinamica);
            if (partes.Count == 0 && !dinamica) continue;
            lista.Add(new { line = Linea(e), text = Compactar(e.ToString()), literal_parts = partes, has_dynamic = dinamica });
        }
        return lista;
    }

    private static void Recorrer(ExpressionSyntax e, List<string> partes, ref bool dinamica)
    {
        switch (e)
        {
            case ParenthesizedExpressionSyntax par:
                Recorrer(par.Expression, partes, ref dinamica);
                break;
            case BinaryExpressionSyntax b when b.IsKind(SyntaxKind.AddExpression):
                Recorrer(b.Left, partes, ref dinamica);
                Recorrer(b.Right, partes, ref dinamica);
                break;
            case LiteralExpressionSyntax l when l.IsKind(SyntaxKind.StringLiteralExpression):
                partes.Add(l.Token.ValueText);
                break;
            case InterpolatedStringExpressionSyntax i:
                foreach (var c in i.Contents)
                {
                    if (c is InterpolatedStringTextSyntax t) partes.Add(t.TextToken.ValueText);
                    else dinamica = true;
                }
                break;
            default:
                if (!EsConstante(e)) dinamica = true;
                break;
        }
    }

    private static List<string> PartesLiterales(ExpressionSyntax e, SyntaxNode contexto)
    {
        var partes = new List<string>();
        var dinamica = false;
        var origen = ExpresionDeVariable(e, contexto) ?? e;
        Recorrer(origen, partes, ref dinamica);
        return partes;
    }

    private static bool EsConcatenacion(ExpressionSyntax e) =>
        (e is BinaryExpressionSyntax b && b.IsKind(SyntaxKind.AddExpression) && ContieneCadena(b))
        || (e is InterpolatedStringExpressionSyntax i && i.Contents.Any(c => c is InterpolationSyntax));

    private static bool ContieneCadena(BinaryExpressionSyntax b) =>
        b.DescendantNodesAndSelf().Any(n =>
            (n is LiteralExpressionSyntax l && l.IsKind(SyntaxKind.StringLiteralExpression)) || n is InterpolatedStringExpressionSyntax);

    // Un nivel hacia atrás: var q = "..." + x;  Metodo(q)
    private static bool VariableConcatenada(ExpressionSyntax e, SyntaxNode contexto)
    {
        var origen = ExpresionDeVariable(e, contexto);
        return origen != null && EsConcatenacion(origen);
    }

    private static ExpressionSyntax? ExpresionDeVariable(ExpressionSyntax e, SyntaxNode contexto)
    {
        if (e is not IdentifierNameSyntax id) return null;
        var metodo = contexto.FirstAncestorOrSelf<BaseMethodDeclarationSyntax>();
        return metodo?.DescendantNodes().OfType<VariableDeclaratorSyntax>()
            .FirstOrDefault(v => v.Identifier.Text == id.Identifier.Text && v.Initializer != null)
            ?.Initializer?.Value;
    }

    private static bool EsConstante(ExpressionSyntax e) =>
        e is LiteralExpressionSyntax
        || (e is MemberAccessExpressionSyntax m && m.Name.Identifier.Text == "Empty" && m.Expression.ToString() is "string" or "String")
        || e is TypeOfExpressionSyntax
        || (e is InvocationExpressionSyntax inv && inv.Expression.ToString() == "nameof");

    // ---------------------------------------------------------------- clases y métodos
    public List<object> Clases(CompilationUnitSyntax raiz)
    {
        var lista = new List<object>();
        foreach (var c in raiz.DescendantNodes().OfType<ClassDeclarationSyntax>())
        {
            lista.Add(new
            {
                name = c.Identifier.Text,
                line = Linea(c),
                modifiers = c.Modifiers.Select(m => m.Text).ToArray(),
                attributes = Atributos(c.AttributeLists),
                bases = c.BaseList?.Types.Select(t => t.Type.ToString()).ToArray() ?? Array.Empty<string>(),
                methods = c.Members.OfType<MethodDeclarationSyntax>().Select(m => new
                {
                    name = m.Identifier.Text,
                    line = Linea(m),
                    modifiers = m.Modifiers.Select(x => x.Text).ToArray(),
                    attributes = Atributos(m.AttributeLists),
                }).ToList(),
            });
        }
        return lista;
    }

    private static string[] Atributos(SyntaxList<AttributeListSyntax> listas) =>
        listas.SelectMany(l => l.Attributes)
            .Select(a => a.Name.ToString().Split('.').Last())
            .Select(n => n.EndsWith("Attribute") ? n[..^"Attribute".Length] : n)
            .ToArray();

    // ---------------------------------------------------------------- bloques catch
    public List<object> Catches(CompilationUnitSyntax raiz)
    {
        var lista = new List<object>();
        foreach (var c in raiz.DescendantNodes().OfType<CatchClauseSyntax>())
        {
            var cuerpo = c.Block;
            lista.Add(new
            {
                line = Linea(c),
                type = c.Declaration?.Type.ToString() ?? "",
                empty = cuerpo.Statements.Count == 0,
                rethrows = cuerpo.DescendantNodes().OfType<ThrowStatementSyntax>().Any()
                           || cuerpo.DescendantNodes().OfType<ThrowExpressionSyntax>().Any(),
                calls = cuerpo.DescendantNodes().OfType<InvocationExpressionSyntax>()
                    .Select(i => Compactar(i.Expression.ToString())).Distinct().ToArray(),
            });
        }
        return lista;
    }

    // ---------------------------------------------------------------- comparaciones
    public List<object> Comparaciones(CompilationUnitSyntax raiz)
    {
        var lista = new List<object>();
        foreach (var b in raiz.DescendantNodes().OfType<BinaryExpressionSyntax>()
                     .Where(b => b.IsKind(SyntaxKind.EqualsExpression) || b.IsKind(SyntaxKind.NotEqualsExpression)))
            lista.Add(new { line = Linea(b), op = b.OperatorToken.Text, left = Compactar(b.Left.ToString()), right = Compactar(b.Right.ToString()) });

        foreach (var inv in raiz.DescendantNodes().OfType<InvocationExpressionSyntax>()
                     .Where(i => UltimoNombre(i.Expression) == "Equals" && i.Expression is MemberAccessExpressionSyntax))
        {
            var m = (MemberAccessExpressionSyntax)inv.Expression;
            var derecho = inv.ArgumentList.Arguments.FirstOrDefault()?.Expression.ToString() ?? "";
            lista.Add(new { line = Linea(inv), op = "Equals", left = Compactar(m.Expression.ToString()), right = Compactar(derecho) });
        }
        return lista;
    }

    // ---------------------------------------------------------------- recursos (IDisposable)
    // Toda variable local inicializada con 'new Tipo(...)'. Qué tipos son
    // IDisposable lo decide la regla (lista de patrones editable).
    public List<object> Disposables(CompilationUnitSyntax raiz)
    {
        var lista = new List<object>();
        foreach (var decl in raiz.DescendantNodes().OfType<LocalDeclarationStatementSyntax>())
        {
            foreach (var v in decl.Declaration.Variables)
            {
                if (v.Initializer?.Value is not BaseObjectCreationExpressionSyntax) continue;
                var nombre = v.Identifier.Text;
                var bloque = decl.Parent;
                var dispuesto = bloque?.DescendantNodes().OfType<InvocationExpressionSyntax>().Any(i =>
                    i.Expression is MemberAccessExpressionSyntax m
                    && m.Expression.ToString() == nombre
                    && m.Name.Identifier.Text is "Dispose" or "Close") ?? false;

                lista.Add(new
                {
                    type = ResolverTipo(decl.Declaration, v),
                    variable = nombre,
                    line = Linea(decl),
                    wrapped_in_using = decl.UsingKeyword.IsKind(SyntaxKind.UsingKeyword) || decl.Parent is UsingStatementSyntax,
                    disposed_explicitly = dispuesto,
                });
            }
        }

        // using (var x = new T()) { ... }  → ya está protegido
        foreach (var u in raiz.DescendantNodes().OfType<UsingStatementSyntax>())
            if (u.Declaration != null)
                foreach (var v in u.Declaration.Variables)
                    lista.Add(new
                    {
                        type = ResolverTipo(u.Declaration, v),
                        variable = v.Identifier.Text,
                        line = Linea(u),
                        wrapped_in_using = true,
                        disposed_explicitly = false,
                    });
        return lista;
    }

    // ---------------------------------------------------------------- utilidades
    // 'var x = new Tipo(...)' → Tipo (sin modelo semántico no se puede más).
    private static string ResolverTipo(VariableDeclarationSyntax decl, VariableDeclaratorSyntax v)
    {
        var tipo = decl.Type.ToString();
        if (tipo == "var" && v.Initializer?.Value is ObjectCreationExpressionSyntax oc)
            return oc.Type.ToString();
        return tipo;
    }

    private static string UltimoNombre(ExpressionSyntax e) => e switch
    {
        MemberAccessExpressionSyntax m => m.Name.Identifier.Text,
        MemberBindingExpressionSyntax mb => mb.Name.Identifier.Text,
        IdentifierNameSyntax i => i.Identifier.Text,
        GenericNameSyntax g => g.Identifier.Text,
        _ => e.ToString(),
    };

    private static string Compactar(string s)
    {
        var t = string.Join(" ", s.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries));
        return t.Length > 300 ? t[..300] : t;
    }
}
