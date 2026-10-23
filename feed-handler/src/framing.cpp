#include "itch/framing.hpp"

#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

#include <cerrno>
#include <cstring>
#include <stdexcept>

namespace itch {

namespace {

[[noreturn]] void fail(const std::string& what, const std::string& path) {
    throw std::runtime_error(what + " '" + path + "': " + std::strerror(errno));
}

}  // namespace

MappedFile::MappedFile(const std::string& path) {
    const int fd = ::open(path.c_str(), O_RDONLY);
    if (fd < 0) {
        fail("cannot open", path);
    }
    struct stat st {};
    if (::fstat(fd, &st) != 0) {
        ::close(fd);
        fail("cannot stat", path);
    }
    size_ = static_cast<std::size_t>(st.st_size);
    if (size_ > 0) {
        void* p = ::mmap(nullptr, size_, PROT_READ, MAP_PRIVATE, fd, 0);
        if (p == MAP_FAILED) {
            ::close(fd);
            fail("cannot map", path);
        }
        ::madvise(p, size_, MADV_SEQUENTIAL);
        data_ = static_cast<const unsigned char*>(p);
    }
    ::close(fd);
}

MappedFile::~MappedFile() {
    if (data_ != nullptr) {
        ::munmap(const_cast<unsigned char*>(data_), size_);
    }
}

void MappedFile::prefault() const {
    const auto page = static_cast<std::size_t>(::sysconf(_SC_PAGESIZE));
    volatile unsigned char sink = 0;
    for (std::size_t i = 0; i < size_; i += page) {
        sink = static_cast<unsigned char>(sink ^ data_[i]);
    }
    (void)sink;
}

}  // namespace itch
