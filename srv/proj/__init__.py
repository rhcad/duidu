from . import view as v, api as a, api_match as m, api_cb as b

handlers = [v.ProjHandler, v.MatchHandler, v.MatchRenderApi, v.ArticleHandler,
            a.ProjAddApi, a.ProjCloneApi, a.ProjEditApi, a.SetEditorApi, a.ImportTextApi,
            a.ArticleEditApi, a.ArticleDelApi, a.SectionDelApi, a.ProjDelApi, a.ReorderColApi,
            b.ImportCBApi, b.ArticleImportCBApi,
            m.SplitApi, m.MergeUpApi, m.MergeRowApi, m.MoveApi, m.MarkDelApi,
            m.TagApi, m.FixRowsApi, m.TocAddApi, m.TocDelApi, m.TocEditApi, m.TocGetApi,
            m.TocImportApi]
