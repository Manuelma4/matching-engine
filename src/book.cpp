#include "me/book.hpp"

namespace me {

// Explicit instantiations keep the matching code compiled once, in this library, for
// every variant (the header declares them extern).
template class Book<Store<MapLevels, StdIndex>>;
template class Book<Store<MapLevels, OpenAddrIndex>>;

}  // namespace me
